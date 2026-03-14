# AI Processing

## Overview

Alfa Hawk integrates external multimodal AI to assist with evidence interpretation, scene description, event reconstruction, and report drafting.

## AI Model

The active provider abstraction in the current implementation is centered on Google Gemini via `GeminiProvider`.

Responsibilities of the AI layer:

- analyze uploaded video evidence
- produce structured JSON
- describe visible observations in neutral language
- support evidence-linked incident reconstruction

## Prompt Design

The provider prompt is designed to enforce:

- observational language
- no unsupported legal conclusions
- no certainty claims beyond visible evidence
- mandatory frame references
- structured JSON output

The system instruction explicitly tells the model to behave as an observer rather than a judge.

## Output Schema

The AI provider interface expects structured output fields such as:

- `executive_summary`
- `key_evidence_observations`
- `scene_description`
- `video_quality_assessment`
- `incident_phases`
- `persons`
- `weapons_objects`
- `timeline`
- `legal_classification`
- `risk_assessment`
- `confidence_matrix`
- `limitations`

## Confidence Scoring

Confidence data is represented as a structured matrix rather than a single blanket score. This allows the platform to expose confidence across different analytical dimensions such as:

- object recognition
- scene understanding
- event reconstruction
- identity consistency

Confidence should be treated as assistive metadata, not proof.

## AI Limitations

Known limitations include:

- hallucinated or missed events
- inaccurate role assignment
- incorrect object or subject descriptions
- sensitivity to lighting, blur, and camera angle
- incomplete reconstruction when key evidence is obscured

## Advisory Role

AI output in Alfa Hawk is advisory. It is meant to accelerate review, not replace certified forensic examination or legal judgment.

## Disclaimer

> This software integrates external AI services for evidence interpretation. AI-generated outputs may contain errors or misinterpretations. Users are responsible for validating all results.

> All generated reports and findings must be independently verified by qualified investigators before being used in legal, regulatory, disciplinary, or official proceedings.

## Practical Review Guidance

- inspect linked evidence frames for each major claim
- compare AI timeline events against original media
- review limitations before escalating findings
- treat legal and threat summaries as preliminary, not determinative
