# Evidence Processing Pipeline

## Overview

Alfa Hawk processes evidence through a staged pipeline that validates media, extracts supporting context, invokes AI analysis, and compiles evidence-linked reports.

## Pipeline Diagram

```mermaid
flowchart LR
    A["Evidence Upload"] --> B["File Validation"]
    B --> C["Metadata Extraction"]
    C --> D["Frame Extraction (OpenCV)"]
    D --> E["AI Analysis"]
    E --> F["Event Reconstruction"]
    F --> G["Evidence Linking"]
    G --> H["Report Compilation"]
```

## 1. Evidence Upload

Evidence is uploaded through the frontend and transferred to the backend API as multipart form data.

Supported production evidence types include:

- video
- image

The uploaded file is read into memory and associated with a short-lived session ID.

Roadmap note:
- deeper audio ingestion and transcript-first analysis remain planned future work

## 2. File Validation

Before analysis starts, the backend validates:

- file presence
- file size
- allowed extension
- basic decodability
- minimum resolution for video
- maximum duration for video
- minimum frame count sanity checks

This stage rejects malformed, unsupported, or operationally unsafe evidence before it reaches the AI layer.

## 3. Metadata Extraction

The backend extracts technical metadata such as:

- media type
- filename
- file size
- width and height
- frame rate
- duration
- codec when available

It also computes a SHA-256 evidence hash for integrity tracking.

## 4. Frame Extraction

For video evidence, Alfa Hawk extracts representative frames using OpenCV-backed logic.

Goals of frame extraction:

- reduce analysis cost and noise
- provide inspectable evidence exhibits
- support incident phases and timeline linking
- preserve timestamps for report traceability

For still images, the system creates a normalized single-frame entry.

## 5. AI Analysis

The evidence engine passes the prepared media to the configured AI provider.

The provider returns structured JSON that can include:

- executive summary
- scene description
- incident phases
- persons
- objects or weapons
- timeline events
- confidence matrix
- limitations

## 6. Event Reconstruction

After AI analysis, Alfa Hawk converts raw structured output into forensic report sections.

This includes:

- chronological phase reconstruction
- timeline event ordering
- evidence frame mapping
- risk and threat summaries

## 7. Evidence Linking

Observations are linked to frame IDs and timestamps wherever possible.

Examples:

- phase cards reference primary evidence frames
- timeline nodes reference clickable frame previews
- report appendices include evidence exhibits and frame indexes

## 8. Report Compilation

The final stage builds:

- a structured report JSON payload
- an evidence-branded PDF report

The generated outputs preserve:

- technical metadata
- evidence integrity references
- frame-linked observations
- platform attribution

## Processing Characteristics

- default storage model: in-memory only
- cleanup model: session TTL plus manual cleanup endpoint
- AI role: advisory interpretation layer
- final responsibility: investigator verification
