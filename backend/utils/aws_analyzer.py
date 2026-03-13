# utils/aws_analyzer.py — AWS Rekognition & Transcribe Integration
import os
import io
import time
import json
import uuid
import boto3
import logging
from dotenv import load_dotenv

load_dotenv(override=True)

from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, AWS_S3_BUCKET_NAME, GEMINI_API_KEY
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

def is_aws_configured():
    return all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, AWS_S3_BUCKET_NAME])

def get_aws_clients():
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )
    s3 = session.client('s3')
    rekognition = session.client('rekognition')
    transcribe = session.client('transcribe')
    return s3, rekognition, transcribe

def upload_to_s3(s3_client, video_bytes, filename):
    """Upload raw video bytes to S3 using a temporary key."""
    ext = os.path.splitext(filename)[1] if filename else '.mp4'
    s3_key = f"evidence_temp_{uuid.uuid4().hex}{ext}"
    try:
        logger.info(f"Uploading video to S3 bucket: {AWS_S3_BUCKET_NAME}, key: {s3_key}...")
        s3_client.upload_fileobj(io.BytesIO(video_bytes), AWS_S3_BUCKET_NAME, s3_key)
        logger.info("S3 upload successful.")
        return s3_key
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        raise e

def delete_from_s3(s3_client, s3_key):
    """Clean up temporary video from S3."""
    try:
        logger.info(f"Deleting {s3_key} from S3...")
        s3_client.delete_object(Bucket=AWS_S3_BUCKET_NAME, Key=s3_key)
        logger.info("S3 cleanup successful.")
    except Exception as e:
        logger.warning(f"Failed to delete {s3_key} from S3: {e}")

# --- REKOGNITION LOGIC ---

def start_rekognition_jobs(rekognition_client, s3_key):
    """Start Text and Label detection jobs."""
    video_def = {'S3Object': {'Bucket': AWS_S3_BUCKET_NAME, 'Name': s3_key}}
    
    # Text Detection (For Number Plates & Signs) - No Filters, send all noise to Gemini
    text_job = rekognition_client.start_text_detection(Video=video_def)
    text_job_id = text_job['JobId']
    
    # Label Detection (For Vehicles, Objects, Accidents, Weather)
    label_job = rekognition_client.start_label_detection(
        Video=video_def,
        Features=['GENERAL_LABELS'],
        MinConfidence=70
    )
    label_job_id = label_job['JobId']
    
    # Person Detection (To count people and track suspects)
    # Removing start_person_tracking as it requires specialized permissions or is restricted. 
    # Label detection will still detect "Person" and "Human" labels.
    
    logger.info(f"Started Rekognition Jobs - Text: {text_job_id[:8]}..., Labels: {label_job_id[:8]}...")
    return text_job_id, label_job_id, None

def wait_for_rekognition_job(rekognition_client, job_type, job_id, callback_func=None):
    """Poll Rekognition until a job completes."""
    max_retries = 120 # 10 minutes max
    for _ in range(max_retries):
        if job_type == 'TEXT':
            response = rekognition_client.get_text_detection(JobId=job_id, MaxResults=1)
        elif job_type == 'LABEL':
            response = rekognition_client.get_label_detection(JobId=job_id, MaxResults=1)
        
        status = response.get('JobStatus')
        if status == 'SUCCEEDED':
            return True
        elif status == 'FAILED':
            logger.error(f"Rekognition Job {job_id} failed.")
            return False
            
        time.sleep(5)
    return False

def fetch_rekognition_results(rekognition_client, job_type, job_id):
    """Fetch paginated results for a completed job."""
    results = []
    next_token = None
    
    while True:
        kwargs = {'JobId': job_id, 'MaxResults': 1000}
        if next_token:
            kwargs['NextToken'] = next_token
            
        if job_type == 'TEXT':
            response = rekognition_client.get_text_detection(**kwargs)
            results.extend(response.get('TextDetections', []))
        elif job_type == 'LABEL':
            response = rekognition_client.get_label_detection(**kwargs)
            results.extend(response.get('Labels', []))
            
        next_token = response.get('NextToken')
        if not next_token:
            break
            
    return results

# --- TRANSCRIBE LOGIC ---

def start_transcribe_job(transcribe_client, s3_key):
    """Start an audio transcription job."""
    job_name = f"Transcribe_{uuid.uuid4().hex}"
    media_uri = f"s3://{AWS_S3_BUCKET_NAME}/{s3_key}"
    
    try:
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': media_uri},
            MediaFormat='mp4', # Transcribe can pull audio from mp4
            LanguageCode='en-US' # default, could use IdentifyLanguage=True
        )
        logger.info(f"Started Transcribe Job: {job_name}")
        return job_name
    except Exception as e:
        logger.error(f"Failed to start Transcribe: {e}")
        return None

def wait_for_transcribe_job(transcribe_client, job_name):
    max_retries = 120
    for _ in range(max_retries):
        response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        status = response['TranscriptionJob']['TranscriptionJobStatus']
        if status == 'COMPLETED':
            # Need to download the transcript JSON
            transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
            return transcript_uri
        elif status == 'FAILED':
            logger.error(f"Transcribe Job {job_name} failed.")
            return None
        time.sleep(5)
    return None

import requests
def download_transcript(transcript_uri):
    if not transcript_uri: return ""
    try:
        r = requests.get(transcript_uri)
        data = r.json()
        transcript = data.get('results', {}).get('transcripts', [{}])[0].get('transcript', '')
        return transcript
    except Exception as e:
        logger.error(f"Failed to download transcript: {e}")
        return ""

# --- LLM SYNTHESIS ---

def synthesize_report_with_llm(raw_text, raw_labels, raw_persons, transcript, metadata, frames=None):
    """Pass all raw AWS timelines AND sample frames to LLM to generate the final structured JSON."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in environment. Please add it to your .env file.")
        
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Process Images for Gemini Multimodal
    image_parts = []
    if frames:
        import base64
        for frame_id, frame_data in frames.items():
            b64_str = frame_data.get('base64', '')
            if b64_str:
                # Convert base64 string back to bytes for google-genai Part
                try:
                    img_bytes = base64.b64decode(b64_str)
                    image_parts.append(
                        types.Part.from_bytes(
                            data=img_bytes,
                            mime_type='image/jpeg'
                        )
                    )
                except Exception as e:
                    logger.warning(f"Could not load frame {frame_id} for Gemini: {e}")
    
    # Condense data to avoid token limits (summarize per second)
    timeline_summary = {} # mapping second -> events
    
    # Group Text (Number Plates / Signs)
    for t in raw_text:
        ts_sec = int(t['Timestamp'] / 1000)
        text = t['TextDetection']['DetectedText']
        conf = t['TextDetection']['Confidence']
        if conf > 5: # Dump almost all text to let Gemini sort out the noise
            if ts_sec not in timeline_summary: timeline_summary[ts_sec] = {'text': [], 'labels': [], 'persons': []}
            if text not in timeline_summary[ts_sec]['text']:
                timeline_summary[ts_sec]['text'].append(text)
                
    # Group Labels (Vehicles, Objects, Environments)
    for l in raw_labels:
        ts_sec = int(l['Timestamp'] / 1000)
        label = l['Label']['Name']
        conf = l['Label']['Confidence']
        if conf > 80:
            if ts_sec not in timeline_summary: timeline_summary[ts_sec] = {'text': [], 'labels': [], 'persons': []}
            if label not in timeline_summary[ts_sec]['labels']:
                timeline_summary[ts_sec]['labels'].append(label)
                
    # Group Persons (Removed explicit Person Tracking, relying on Labels now for "Person")
    for p in raw_persons:
        pass

    # Format timeline for LLM
    timeline_str = "AWS REKOGNITION VIDEO TIMELINE:\n"
    for sec in sorted(timeline_summary.keys()):
        events = timeline_summary[sec]
        if events['text'] or events['labels'] or events['persons']:
            ts_formatted = time.strftime('%H:%M:%S', time.gmtime(sec))
            timeline_str += f"[{ts_formatted}] "
            if events['text']: timeline_str += f"Text Detected: {', '.join(events['text'])} | "
            if events['labels']: timeline_str += f"Objects: {', '.join(events['labels'][:10])} | "
            if events['persons']: timeline_str += f"People Count: {len(events['persons'])}"
            timeline_str += "\n"

    # Add Transcribe details
    audio_str = f"\nAWS TRANSCRIBE AUDIO LOG:\n{transcript}\n" if transcript else "\nAWS TRANSCRIBE AUDIO LOG:\nNo speech detected.\n"

    llm_prompt = f"""You are a senior forensic evidence analyst compiling a final structured JSON report based on highly accurate AWS Vide Intelligence data and 30 raw video frames.
    
    Analyze the following AWS metadata, timeline arrays, AND the attached raw image frames (if provided) to construct a comprehensive forensic picture.
    
    CRITICAL VISION TASKS:
    1. You MUST look closely at the attached image frames for license plates or text. Do not rely entirely on the AWS timeline for this. If you see text in the image that looks like a vehicle plate, extract it exactly as written.
    2. Analyze the images for complex actions (e.g. physical altercations, weapons, erratic movement). The AWS timeline will only give you raw labels like 'Person' or 'Tool'. You must use your eyes on the frames to describe exactly what is happening.
    
    Look for intersections (e.g., if "Car" and a number plate text are seen at the exact same second, map that plate to the car).
    
    {timeline_str}
    {audio_str}
    
    Return ONLY valid JSON in this exact format (no markdown, no code fences):
    {{
        "executive_summary": "A 2-3 sentence overview of what this evidence shows based on the AWS data.",
        "scene_description": "Detailed description of the scene and environment.",
        "violations": [
            {{
                "type": "traffic/criminal/safety/regulatory",
                "description": "Detailed description of the violation",
                "severity": "critical/high/medium/low",
                "detected_at_timestamp": "Timestamp (e.g. 00:00:15) where evidence strongly suggests this occurred",
                "evidence_details": "What in the AWS data supports this"
            }}
        ],
        "accidents": [],
        "number_plates": [
            {{
                "plate_text": "EXACT text detected as a plate",
                "vehicle_type": "car/truck/motorcycle/etc (infer from nearby labels)",
                "detected_at_timestamp": "Timestamp where it was clearest",
                "confidence": "high/medium/low based on frequency"
            }}
        ],
        "human_faces": [
            {{
                "person_id": "Person 1",
                "description": "Infer activity based on timeline",
                "detected_at_timestamp": "Timestamp"
            }}
        ],
        "landmarks": [],
        "objects_of_interest": [
             {{
                "object": "Name of salient object (Weapons, specific items)",
                "description": "Why it is relevant",
                "condition": "N/A"
            }}
        ],
        "timeline_events": [
            {{
                "time_indicator": "00:00:05",
                "event": "Description of what happened"
            }}
        ],
        "forensic_observations": "Summary of audio or overall flow",
        "confidence_score": 0.95
    }}"""
    
    contents = [llm_prompt]
    contents.extend(image_parts)
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction="You are a multimodal forensic reporting machine. Extract text/plates from images meticulously. Output ONLY raw parseable JSON.",
            temperature=0.1,
            response_mime_type="application/json",
        )
    )
    
    result_text = response.text.strip()
    
    # Strip markdown if present
    if result_text.startswith('```json'): result_text = result_text[7:]
    elif result_text.startswith('```'): result_text = result_text[3:]
    if result_text.endswith('```'): result_text = result_text[:-3]
    result_text = result_text.strip()
    
    return json.loads(result_text)

# --- MAIN ENTRYPOINT ---

def analyze_video_aws(video_bytes, filename, metadata, frames=None, progress_callback=None):
    """Orchestrates the full AWS Intelligence Pipeline."""
    
    def update_prog(p, m):
        if progress_callback: progress_callback(p, m)
        logger.info(f"AWS Analyst: {p}% - {m}")

    if not is_aws_configured():
        raise Exception("AWS Credentials or S3 Bucket not fully configured.")

    s3_client, rekognition_client, transcribe_client = get_aws_clients()
    s3_key = None

    try:
        # 1. Upload Video
        update_prog(15, "Uploading high-res video to AWS S3 secure bucket...")
        s3_key = upload_to_s3(s3_client, video_bytes, filename)
        
        # 2. Start Jobs
        update_prog(25, "Initiating AWS Rekognition & Transcribe background jobs...")
        text_id, label_id, person_id = start_rekognition_jobs(rekognition_client, s3_key)
        transcribe_id = start_transcribe_job(transcribe_client, s3_key)

        # 3. Poll Jobs
        update_prog(30, "Awaiting AWS Rekognition Number Plate & Signage scanning...")
        wait_for_rekognition_job(rekognition_client, 'TEXT', text_id)
        
        update_prog(40, "Awaiting AWS Rekognition Vehicle & Object detection...")
        wait_for_rekognition_job(rekognition_client, 'LABEL', label_id)
        
        transcript_uri = None
        if transcribe_id:
            update_prog(60, "Awaiting AWS Transcribe Audio processing...")
            transcript_uri = wait_for_transcribe_job(transcribe_client, transcribe_id)

        # 4. Fetch Results
        update_prog(70, "Downloading detailed forensic data from AWS servers...")
        raw_text = fetch_rekognition_results(rekognition_client, 'TEXT', text_id)
        raw_labels = fetch_rekognition_results(rekognition_client, 'LABEL', label_id)
        raw_persons = [] # Person tracking disabled due to IAM
        transcript = download_transcript(transcript_uri)

        # 5. Connect the dots with LLM + Vision
        update_prog(80, "Applying Multimodal LLM Synthesis to AWS timeline + Video frames...")
        final_report_structured = synthesize_report_with_llm(raw_text, raw_labels, raw_persons, transcript, metadata, frames)
        
        return final_report_structured

    except Exception as e:
        logger.error(f"AWS Video Analysis Pipeline Failed: {e}", exc_info=True)
        raise e

    finally:
        # 6. Cleanup S3
        if s3_key:
            update_prog(90, "Cleaning up temporary files from AWS S3...")
            delete_from_s3(s3_client, s3_key)
