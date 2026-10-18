# Grade Service

Production-oriented REST API for managing students, subjects and grades. This is laboratory work 10 for variant 7, built as the final production release of the student grading system.

## Features

- students, subjects and grade persistence with SQLAlchemy and SQLite;
- grade creation, update and deletion;
- average, minimum, maximum, performance category, ranking and threshold search;
- FastAPI endpoints `/students`, `/subjects`, `/grades`, `/students/{id}/average`;
- `/health`, `/docs`, `/redoc` and `/openapi.json`;
- environment-based configuration and production logging;
- NumPy analytics, profiling and benchmarks retained from Lab_09;
- automated tests with an 80% coverage threshold;
- wheel and source distribution packaging;
- multi-stage, non-root Docker image with healthcheck and persistent volume;
- GitHub Actions for Ruff, formatting, mypy, pytest, package build and Docker verification.

## Requirements

- Python 3.11 or 3.12;
- Docker for container execution;
- Git for version control.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## Configuration

Copy the documented template. The real `.env` file is ignored by Git and must not contain committed secrets.

```bash
cp .env.example .env
```

Supported environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `Grade Service` | OpenAPI application name |
| `APP_ENV` | `development` | `development`, `test` or `production` |
| `DATABASE_URL` | `sqlite:///data/grading.db` | SQLAlchemy database URL |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `API_KEY` | empty | Optional runtime secret, never committed |

Example without changing source code:

```bash
export APP_ENV=production
export LOG_LEVEL=WARNING
export DATABASE_URL=sqlite:///data/grading.db
```

## Running locally

```bash
grade-service
```

Alternative:

```bash
uvicorn grade_service.api:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | service status, environment and version |
| `GET/POST` | `/students` | ranking/filtering and student creation |
| `GET/POST` | `/subjects` | subject listing and creation |
| `GET/POST` | `/grades` | grade listing and creation |
| `GET` | `/students/{id}/grades` | student grades |
| `GET` | `/students/{id}/average` | average/min/max/performance |
| `PATCH/DELETE` | `/grades/{id}` | update or delete a grade |

Interactive documentation: `http://localhost:8000/docs`.

## Quality and tests

```bash
ruff check .
ruff format --check .
mypy src
pytest -q
```

The pytest configuration enforces at least 80% total coverage.

## Package build

```bash
python -m build
ls -la dist
```

The build produces:

- `grade_service-1.0.0-py3-none-any.whl`;
- `grade_service-1.0.0.tar.gz`.

Install the wheel in a clean environment:

```bash
python -m venv /tmp/grade-service-check
/tmp/grade-service-check/bin/pip install dist/grade_service-1.0.0-py3-none-any.whl
/tmp/grade-service-check/bin/grade-service --help
```

## Docker

Build and start the hardened image:

```bash
docker build -t grade-service:1.0.0 .
docker run --rm -p 8000:8000 \
  -e APP_ENV=production \
  -e LOG_LEVEL=INFO \
  -e DATABASE_URL=sqlite:////app/data/grading.db \
  -v grade_data:/app/data \
  grade-service:1.0.0
```

The final image uses a non-root user, multi-stage wheel installation and Docker `HEALTHCHECK`. Docker Compose is also provided:

```bash
cp .env.example .env
docker compose up --build
```

## CI/CD

`.github/workflows/ci.yml` runs on every push to `main` and every pull request. It checks Python 3.11 and 3.12, uploads wheel/sdist artifacts, builds the Docker image, starts a container and verifies `/health`.

No deployment credential is stored in source code. Real PyPI or registry tokens must be added as GitHub Secrets and referenced as `${{ secrets.NAME }}`.

## Project structure

```text
Lab_10/
├── src/grade_service/     application package
├── tests/                 unit and integration tests
├── migrations/            Alembic migrations
├── benchmarks/results/    Lab_09 optimization evidence
├── report/report.docx     laboratory report
├── Dockerfile             multi-stage production image
├── docker-compose.yml     container orchestration
├── .env.example           configuration template
├── .dockerignore          Docker build exclusions
└── pyproject.toml         package and quality configuration
```

## Demonstration scenario

1. Show repository structure and environment configuration.
2. Run Ruff, mypy and pytest.
3. Build wheel and sdist and install the wheel.
4. Build and run the Docker image with a persistent volume.
5. Show `/health`, `/docs` and the grading endpoints.
6. Show the green GitHub Actions workflow and uploaded distributions.

## Author

Заставний Денис, ФеП-32. Subject: `professional_python`. Variant 7.
