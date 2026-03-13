# Smart Evidence Writer

An open-source, AI-powered forensic evidence analysis platform that generates structured law enforcement and legal reports. 
Designed with privacy at its core: **all processing is strictly in-memory** — no data or files are persisted to disk or cloud storage.

## Features

- **Upload Evidence**: Supports images, videos, and audio.
- **AI Analysis**: Integrates with Groq Llama 3.2 Vision model (or compatible alternatives) for rapid, intelligent parsing.
- **Smart Frame Extraction**: Uses OpenCV for intelligent video frame extraction targeting violations, faces, plates, and landmarks.
- **Deep AWS Rekognition Integration** (Optional): Extends capability with AWS Rekognition for deep forensic analysis.
- **Structured Reporting**: Produces detailed police/legal report formats including:
  - Violations detected (with severity)
  - Accident analysis
  - Number plate registry
  - Persons identified (faces)
  - Chronological timeline
  - Risk assessment & Investigative recommendations
- **PDF Export**: Downloads cleanly formatted PDF reports with embedded evidence frames.
- **Zero Footprint**: In-memory only processing. Sessions automatically expire after 30 minutes.

## Tech Stack

- **Backend**: Python, Flask
- **AI / LLM**: Groq API (Llama Vision/Text)
- **Frame Extraction & Image Processing**: OpenCV, Pillow
- **Audio Transcription**: SpeechRecognition
- **Report Generation**: ReportLab
- **Frontend**: Vanilla HTML / CSS / JavaScript

## Quick Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Godwin1603/smart-evidence-writer.git
   cd smart-evidence-writer
   ```

2. **Install Python dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   Copy the example environment files and add your API keys.
   ```bash
   cp .env.example .env
   cp backend/.env.example backend/.env
   ```
   Add your keys into the `.env` files (e.g., Groq API Key).

4. **Run the Server:**
   ```bash
   python app.py
   ```

5. **Open the Application:**
   Visit `http://localhost:5000` in your web browser.

## Security & Privacy Note

- **No Data Retention.** All uploads are processed strictly in RAM and dismissed post-analysis or upon session expiry (30 minutes).
- **Public Sandbox Safe.** Ensure you do NOT commit your `.env` files. Ensure you utilize the `.env.example` templates provided.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
