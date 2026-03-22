# Contributing

Thanks for contributing to Alfa Hawk.

## Workflow (Required)

We use a safe workflow to protect production deployments:

`feature/*` → `dev` → `main` → production

- **Do all work in feature branches** (never commit directly to `main`)
- **Open a PR into `dev`** for review and staging/testing
- After validation, **merge `dev` → `main`** via PR (production release)

## Branch naming

- `feature/<short-description>`
- `fix/<short-description>`
- `chore/<short-description>`

Examples:

- `feature/evidence-viewer-sync`
- `fix/usage-counter-mapping`

## Pull request process (Forks)

External contributors must follow this process:

1. Fork the repository
2. Create a feature branch from `dev`
3. Make changes with focused commits
4. Open a pull request **into `dev`**
5. Address review feedback

Direct pushes to protected branches are not allowed.

## Coding guidelines

- **No secrets in code**: never commit `.env` files, API keys, credentials, or private URLs.
- Keep the UI style **dark graphite / muted steel**; avoid flashy gradients.
- Backend changes should keep evidence processing **in-memory** by default.
- Prefer small, reviewable PRs.

## Local development

Backend:

- Install: `pip install -r backend/requirements.txt`
- Run: `python backend/app.py`

Frontend:

- Served by backend by default from `frontend/`

## Tests

Run unit tests:

- `python -m unittest discover -s tests -p "*_test.py"`

