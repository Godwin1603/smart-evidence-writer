# Alfa Hawk -- Professional Forensic Evidence Workstation

Current Version: `v1.0.0`

Alfa Hawk is an AI-assisted forensic evidence analysis platform for image and video investigations. It processes evidence in memory, links observations to exhibits and timelines, and generates structured JSON and PDF reports with Alfa Hawk watermarking and integrity metadata.

## Live Demo

- Frontend UI: [https://app.alfagroups.tech](https://app.alfagroups.tech)
- Backend API: [https://api.alfagroups.tech](https://api.alfagroups.tech)

## Architecture Overview

- `frontend/` -- workstation UI built with HTML, CSS, and vanilla JavaScript
- `backend/app.py` -- Flask API server and in-memory session coordinator
- `backend/engine/` -- evidence processing, metadata extraction, and frame extraction
- `backend/ai_providers/` -- Gemini provider abstraction
- `backend/reporting/` -- structured report builder, PDF generator, watermarking, and integrity hashing
- `docs/` -- system, deployment, privacy, security, and API documentation

## Quickstart Guide

1. Clone the repository.
   ```bash
   git clone https://github.com/Godwin1603/smart-evidence-writer.git
   cd smart-evidence-writer
   ```
2. Install dependencies.
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Create `.env` from `.env.example` and set your Gemini API key.
   ```env
   GEMINI_API_KEY=
   GLOBAL_DAILY_LIMIT=200
   MAX_UPLOAD_SIZE=52428800
   MAX_VIDEO_DURATION=60
   RATE_LIMIT_COOLDOWN=30
   PORT=5000
   CORS_ALLOWED_ORIGINS=https://app.alfagroups.tech
   CLIENT_HOURLY_LIMIT=1
   CLIENT_DAILY_LIMIT=3
   ```
4. Start locally with Flask.
   ```bash
   python backend/app.py
   ```
5. Start in production with Gunicorn.
   ```bash
   gunicorn backend.app:app
   ```

## Example Report

Generated reference reports are included in `examples/`:

- `examples/example_analysis.json`
- `examples/sample_report.pdf`
- `examples/AlfaHawk_Forensic_Report_227594d2.pdf`
- `examples/Forensic_Report_5af81eae.pdf`
- `examples/Evidence_Report_ (5).pdf`

## Documentation Links

- `docs/system-overview.md`
- `docs/architecture.md`
- `docs/evidence-processing.md`
- `docs/deployment.md`
- `docs/privacy-model.md`
- `docs/ai-processing.md`
- `docs/report-structure.md`
- `docs/security.md`
- `docs/api-reference.md`
- `docs/quickstart.md`
- `docs/roadmap.md`

## Production Notes

- Default production routing assumes `app.alfagroups.tech` for the UI and `api.alfagroups.tech` for the API.
- Evidence is processed in memory and temporary files are cleaned from the system temp directory after use.
- Upload validation occurs before AI processing and currently accepts `mp4`, `mov`, `avi`, `jpg`, `jpeg`, `png`, and `wav`.
- The current investigation pipeline is production-ready for image and video analysis. WAV uploads are validated at ingress, but full audio AI analysis is not part of `v1.0.0`.

## License and Branding

The source code is released under the MIT License. Branding for Alfa Hawk, Alfa Labs, and related marks remains protected as described in `TRADEMARK.md`. Alfa Hawk is a platform under Alfa Labs, a child company of Alfa Groups.
