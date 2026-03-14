# Alfa Hawk Core

This directory documents the intended open-source core boundary for Alfa Hawk.

## Intended Scope

The core package should remain usable under the repository's MIT-licensed code terms with user-provided AI credentials. The target scope includes:

- analysis engine
- evidence processing logic
- frame extraction
- report builder
- AI provider interface

## Current Repository Mapping

Today, the closest equivalent components live in:

- `backend/ai_providers/`
- `backend/engine/evidence_engine.py`
- `backend/engine/frame_extractor.py`
- `backend/engine/media_processor.py`
- `backend/engine/ocr_processor.py`
- `backend/reporting/report_builder.py`
- `backend/reporting/pdf_generator.py`

## Separation Goal

The long-term goal is to keep these capabilities independently runnable without requiring Alfa Labs hosted infrastructure. A future extraction can move these components into a dedicated reusable package while preserving backward compatibility for self-hosted users.
