# Alfa Hawk Platform

This directory documents the intended hosted-platform boundary for Alfa Hawk.

## Intended Scope

The platform layer represents service features and deployment-specific capabilities for Alfa Hawk under Alfa Labs, a child company of Alfa Groups, such as:

- API server
- rate limiting and abuse controls
- usage tracking
- watermark and attribution enforcement
- hosted UI components

## Current Repository Mapping

Today, the closest equivalent components live in:

- `backend/app.py`
- `backend/config.py`
- `frontend/`

## Separation Goal

The hosted platform should be able to evolve independently from the open-source core while continuing to consume the same analysis primitives. This boundary is intended to support:

- public open-source releases of the core
- self-hosting with user-provided AI keys
- Alfa Labs-operated managed deployments with additional service controls
