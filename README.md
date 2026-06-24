# Photo → CAD

Convert a single photograph of a building façade into a scaled, layered
vector elevation drawing — exported as **.png** and **.dxf** (AutoCAD /
Rhino-ready) — entirely **offline**, no cloud services.

Full architecture, rationale, and roadmap: [`docs/architecture.md`](docs/architecture.md).

> **Status:** Phase 1 — project skeleton. No pipeline logic yet; this commit
> proves the GUI, packaging, dependency, and i18n foundations all work
> together before any computer-vision code is written.

## Requirements

- **Python 3.12**
- Windows for the shipped app; the CV/ML core can be developed on macOS/Linux too.

## Setup

A virtual environment is never committed to git — create your own with the
provided script, which installs the locked dependencies from
`requirements.txt` (runtime) and `requirements-dev.txt` (tooling).

**Windows:**

```powershell
powershell -ExecutionPolicy Bypass -File setup_env.ps1
```

**macOS / Linux (development only):**

```bash
./setup_env.sh
```

Both scripts create `.venv/`, activate it, upgrade pip, and install
`requirements.txt` + `requirements-dev.txt`.

## Running

```powershell
# after activating .venv
python src\app\main.py     # Windows
python src/app/main.py     # macOS/Linux
```

This currently opens an empty window — confirms PySide6, the i18n loading
path, and the package layout all work.

## Tests

```bash
pytest
```

Runs headless (`QT_QPA_PLATFORM=offscreen`, set in `tests/conftest.py`) so
it works in CI with no display.

## Updating dependencies

Edit `requirements.in` / `requirements-dev.in` (unpinned, top-level), then
re-lock:

```bash
pip-compile requirements.in -o requirements.txt
pip-compile requirements-dev.in -o requirements-dev.txt
```

## Project layout

```
src/app/
  ui/              PySide6 widgets, view-models, editing canvas
  application/      use-cases, pipeline orchestrator, Protocols, undo/redo
  domain/           DrawingModel, Layer, Stroke, ScaleCalibration, value objects
  infrastructure/   adapters: opencv (vision/), onnxruntime (ml/), ezdxf (export/), persistence/
  composition.py    DI composition root — the only place concretes meet Protocols
models/             *.onnx + *.sha256 (binaries git-ignored; see .gitignore)
i18n/               app_en.ts / app_es.ts (compiled .qm is a build artifact, git-ignored)
tests/              unit/integration tests, headless Qt config
packaging/          PyInstaller .spec, Inno Setup .iss, signing scripts (Phase 5)
docs/               architecture.md and future ADRs
```

## License

TBD.
