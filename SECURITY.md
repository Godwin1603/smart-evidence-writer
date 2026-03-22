# Security Policy

## Supported Versions

This project is maintained on the `main` branch. Security fixes are released as soon as practical.

## Reporting a Vulnerability

Please **do not** open public GitHub issues for security vulnerabilities.

Instead, report privately using one of the following:

- **Email**: `contact@alfagroups.tech` (preferred)

When reporting, include:

- A clear description of the vulnerability and impact
- Steps to reproduce (PoC if possible)
- Affected commit / branch / deployment (if known)
- Any logs or screenshots that help triage

We will acknowledge receipt and work with you on a coordinated disclosure timeline.

## Scope Notes

- **Secrets**: API keys must be provided via environment variables (see `.env.example`). Do not commit credentials.
- **Uploads**: The backend enforces file validation and limits. Deployments should enforce HTTPS and restrict debug routes.

For more details on platform hardening, see `docs/security.md`.

