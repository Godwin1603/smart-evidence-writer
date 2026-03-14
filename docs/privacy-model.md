# Privacy Model

## Overview

Alfa Hawk is designed around a privacy-preserving evidence workflow in which uploaded evidence is processed in volatile memory and is not intended to be retained permanently by the default application path.

## Core Privacy Principles

- in-memory evidence processing
- short-lived sessions
- no intentional permanent evidence storage by default
- explicit disclosure when external AI processing is used

## In-Memory Evidence Processing

Uploaded files are read into application memory and associated with a temporary session. Evidence bytes, extracted frames, report JSON, and generated PDF data remain tied to that volatile session.

## No Persistent Evidence Storage

The default implementation is intended to avoid permanent storage of evidence on local disk or database systems as part of normal operation.

Example statement:

> All evidence files are processed in volatile memory and are not stored on disk or database systems. Processing artifacts are removed after report generation.

## Temporary Artifact Cleanup

The backend uses:

- session TTL cleanup
- manual cleanup endpoint support
- provider-side cleanup attempts after AI processing

The current session cleanup timer removes expired sessions after the configured retention window.

## External AI Processing Disclosure

When AI analysis is enabled, evidence may be transmitted temporarily to an external AI service provider for interpretation. That introduces a separate processing boundary outside the Alfa Hawk runtime.

Users should review:

- provider terms
- provider retention behavior
- provider regional processing implications
- internal legal and compliance requirements

## Operational Caveats

While the default design is privacy-oriented, deployers should still evaluate:

- server logs
- reverse proxy logs
- crash dumps
- monitoring tooling
- temporary files created by third-party libraries or custom deployment scripts

## Recommended Privacy Controls

- minimize log verbosity in production
- restrict access to debug endpoints
- apply short TTL values for sensitive workflows
- isolate enterprise deployments if data residency is required
- document any deployment-specific storage exceptions clearly
