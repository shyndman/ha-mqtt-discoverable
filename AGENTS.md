# Repository Guidelines

## Project Structure & Module Organization
- Library code lives in `ha_mqtt_discoverable/`, with entity implementations in `sensors.py`, device helpers in `settings.py`, and CLI glue under `ha_mqtt_discoverable/cli/`.
- Integration tests target the public API via `tests/test_*.py`; they rely on stubbed MQTT objects, so keep imports side-effect free.
- Supporting assets sit in `scripts/`, `bin/`, and Dockerfiles; look at the `Makefile` for the blessed workflows.

## Build, Test, and Development Commands
- `poetry install` – create the virtualenv with pinned dependencies from `poetry.lock`.
- `poetry run ruff check ha_mqtt_discoverable tests` – lint and format; `make format` wraps the same command.
- `poetry run pytest -q` or `make test` – run the suite.
- `make wheel` – clean, lint, and build the distribution wheel.
- `make multiarch_image` / `make local` – build Docker images used for trialing changes; run only when you need container artifacts.

## Coding Style & Naming Conventions
- Target Python 3.10+; stay type-hint complete, mirroring existing annotations in `settings.py` and `sensors.py`.
- Use 4-space indentation, snake_case for functions/modules, PascalCase for entity classes (e.g., `BinarySensorInfo`).
- Run `ruff` before pushing; do not disable lint rules without discussion.

## Testing Guidelines
- Tests live in `tests/`, named `test_<topic>.py`. Mirror fixtures and descriptive names (`test_generate_config`, `test_boolean_state`).
- Prefer pytest fixtures and parametrization to reduce MQTT setup duplication.
- Maintain coverage for every entity type; add happy-path, edge-case, and MQTT message tests.
- Run `poetry run pytest -q` locally and keep assertions independent of real brokers.

## Commit & Pull Request Guidelines
- Follow the repo’s short, imperative subjects (`Upgrade to Pydantic 2.11.9`, `Migrate to typed callbacks`). Keep body lines wrapped ~72 chars explaining motivation and testing.
- Open PRs with: 1) summary of change and rationale, 2) testing evidence (commands + results), 3) related issue link, 4) screenshots or payload snippets when affecting discovery output.
- Rebase before requesting review; avoid force-pushing after review unless requested, and keep PRs focused.

## Security & Configuration Tips
- Never commit broker credentials; prefer `.env` entries referenced via `Settings.MQTT`.
- Docker images embed the wheel; regenerate with `make wheel` before publishing, and confirm `MODULE_VERSION` matches `pyproject.toml` to avoid shipping stale code.
