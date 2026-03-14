# Deployment Guide

## Deployment Overview

Alfa Hawk can be deployed for local development, internal self-hosting, or hosted platform use. The recommended public architecture separates the workstation UI from the API runtime:

- Railway service rooted at `backend/`
- Vercel project rooted at `frontend/`
- optional second Vercel project rooted at `product-page/`
- Cloudflare DNS:
  - `app.alfagroups.tech` -> `cname.vercel-dns.com`
  - `api.alfagroups.tech` -> Railway service hostname

High-level runtime pattern:

```mermaid
flowchart LR
    U["User Browser"] --> F["Vercel Frontend UI"]
    F --> B["Railway Backend API"]
    B --> E["Evidence Processing Engine"]
    E --> G["External AI Service (Gemini)"]
```

## Environment Requirements

Recommended baseline:

- Python 3.11+
- pip
- OpenCV-compatible runtime
- FFmpeg available for richer media workflows
- Gunicorn for VPS or container production serving
- network access to the external AI provider when using hosted AI analysis

Operational considerations:

- sufficient RAM for in-memory evidence sessions
- outbound access to Gemini APIs when AI analysis is enabled
- reverse proxy or managed platform ingress for production deployments

## Local Development Setup

1. Clone the repository.
2. Install backend dependencies.
3. Configure environment variables.
4. Start the Flask backend.
5. Access the web UI through the backend host.

Example:

```bash
git clone https://github.com/Godwin1603/smart-evidence-writer.git
cd smart-evidence-writer
pip install -r backend/requirements.txt
python backend/app.py
```

Production command example from the repo root:

```bash
gunicorn -w 2 -b 0.0.0.0:${PORT:-5000} backend.app:app
```

When deploying Railway with `backend/` as the service root, use:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

## Cloud Deployment

Typical cloud deployment layout:

- Railway or container service running the Flask backend
- static frontend hosted separately on Vercel
- outbound access to AI provider APIs

For hosted deployments, consider:

- TLS termination
- request timeouts suitable for video analysis
- horizontal scaling with externalized shared state if moving beyond single-instance memory sessions

## Environment Variables

Known environment variables in the current codebase include:

- `GEMINI_API_KEY`
- `PORT`
- `FLASK_DEBUG`
- `ENABLE_DEBUG_ROUTES`
- `CORS_ALLOWED_ORIGINS`
- `MAX_UPLOAD_SIZE`
- `MAX_VIDEO_DURATION`
- `GLOBAL_DAILY_LIMIT`
- `RATE_LIMIT_COOLDOWN`
- `CLIENT_HOURLY_LIMIT`
- `CLIENT_DAILY_LIMIT`
- `IP_HOURLY_LIMIT`
- `IP_DAILY_LIMIT`
- `MAX_CONCURRENCY_PER_CLIENT`
- `MAX_CONCURRENCY_PER_IP`

Practical note:

- the current provider abstraction and primary forensic workflow are Gemini-oriented
- the current deployable pipeline supports image and video evidence
- deeper audio workflows remain roadmap work and should not be advertised as production-ready yet

## Scaling Considerations

The current implementation uses in-memory session storage and in-process tracking maps.

This is suitable for:

- local development
- demos
- controlled single-instance deployments

For production scaling, consider replacing in-memory state with:

- Redis for sessions and quotas
- persistent job queue for long-running analyses
- object storage only if your privacy model explicitly allows it

## Deployment Recommendations

- Keep upload size and duration limits enforced at both proxy and app layers.
- Run the service behind a reverse proxy or managed platform ingress.
- Restrict debug endpoints in non-development environments.
- Set `CORS_ALLOWED_ORIGINS=https://app.alfagroups.tech` for the public frontend.
- Keep the frontend API base pointed at `https://api.alfagroups.tech`.
- Monitor memory pressure due to in-memory media handling.
- Use BYO AI mode for isolated customer-controlled deployments where appropriate.
- For Cloudflare, disable proxying on the API CNAME if Railway TLS/origin behavior requires direct origin access.
