# Security

## Overview

Alfa Hawk includes baseline operational and application-layer controls intended to reduce misuse, unsafe uploads, and integrity gaps in evidence processing.

## File Upload Validation

The backend validates uploads for:

- presence and non-empty content
- supported file extensions
- maximum file size
- video decodability
- minimum video resolution
- maximum video duration
- minimum frame count sanity

These checks help prevent malformed or oversized media from entering the analysis path.

## Rate Limiting and Abuse Controls

The current backend enforces:

- per-client monthly limits
- per-IP monthly limits
- cooldown windows between requests
- per-client concurrency limits
- per-IP concurrency limits
- global daily platform capacity controls

These protections are currently implemented in memory and are suitable for controlled deployments. Production-grade hosting should externalize this state.

## API Key Handling

Alfa Hawk supports:

- platform-managed AI configuration
- BYO AI key submission for user-controlled analysis

The current upload route performs basic BYO key validation and masks keys in operational logging. Deployers should still ensure keys are:

- transmitted only over TLS
- never persisted unintentionally
- redacted from logs and monitoring systems

## Evidence Hashing

The backend computes SHA-256 hashes for uploaded evidence to support integrity-aware workflows and report metadata generation.

## Report Integrity Hashing

The report pipeline computes a report-level integrity hash so that generated outputs can be tied to a specific structured report state.

## Session Security Considerations

- sessions are short-lived
- expired sessions are cleaned automatically
- frames and reports are tied to session IDs
- debug endpoints should be restricted or disabled in production

## Recommended Hardening

- place the backend behind a reverse proxy
- enforce HTTPS
- remove or protect debug routes
- externalize quotas and state for multi-node deployments
- apply authentication for enterprise deployments
- add audit logging where legally appropriate
