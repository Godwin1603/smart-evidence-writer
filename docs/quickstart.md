# Quickstart

## Prerequisites

- Python 3.11+
- pip
- internet access for external AI analysis when using Gemini

## Setup

```bash
git clone https://github.com/Godwin1603/smart-evidence-writer.git
cd smart-evidence-writer
pip install -r backend/requirements.txt
```

## Configure Environment

Create or update `.env` or `backend/.env` with the required values:

```env
GEMINI_API_KEY=your_key_here
PORT=5000
FLASK_DEBUG=false
ENABLE_DEBUG_ROUTES=false
CORS_ALLOWED_ORIGINS=http://localhost:5000,http://127.0.0.1:5000
MAX_UPLOAD_SIZE=50
MAX_VIDEO_DURATION=60
GLOBAL_DAILY_LIMIT=500
```

## Run the Server

```bash
python backend/app.py
```

## Access the UI

Open your browser and navigate to:

```text
http://localhost:5000
```

## Basic Usage

1. Upload a video or image file.
2. Enter optional case metadata.
3. Start analysis.
4. Wait for the asynchronous pipeline to complete.
5. Review the generated Overview, Timeline, Frames, and Export sections.
6. Download the JSON or PDF report if needed.

## Reference Reports

If you want to understand the expected final output before running the platform, open the included generated reference reports:

- [AlfaHawk_Forensic_Report_227594d2.pdf](C:\smart-evidence-writer\examples\AlfaHawk_Forensic_Report_227594d2.pdf)
- [Forensic_Report_5af81eae.pdf](C:\smart-evidence-writer\examples\Forensic_Report_5af81eae.pdf)
- [Evidence_Report_ (5).pdf](C:\smart-evidence-writer\examples\Evidence_Report_%20(5).pdf)

## BYO AI Mode

If you prefer to use your own Gemini key:

1. enter the key in the UI
2. upload evidence
3. proceed with analysis using the validated BYO key path

## Troubleshooting

- If upload fails, check file size, file extension, and media decodability.
- If analysis does not start, ensure `X-Client-ID` is being sent by the frontend and that rate limits have not been hit.
- If AI analysis fails, verify Gemini key validity and provider availability.
- If you host the frontend separately, set the API base via the `alfa-hawk-api-base` meta tag or `window.ALFA_HAWK_API_BASE`.
