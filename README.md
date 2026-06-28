# Photo → CAD

Convert a single photograph of a building façade into a scaled, layered
vector elevation drawing — exported as **.png** and **.dxf** (AutoCAD /
Rhino-ready) — entirely **offline**, no cloud services.

Full architecture, rationale, and roadmap: [`docs/architecture.md`](docs/architecture.md).

> **Status:** the core pipeline (ImageValidator → Rectifier → EdgeDetector
> → Vectorizer → GeometryRegularizer → ScaleCalibrator → both exporters)
> is implemented, tested, and wired into a working GUI — `composition.py`
> assembles a real `PhotoToCadPipeline`, and the app actually produces a
> `.png` and a `.dxf` from a photo today. Manual corner-picking only (no
> automatic perspective detection yet); `Preprocessor` and
> `FacadeSegmenter` (Phase 3 semantic segmentation) don't exist yet
> either. See [`docs/architecture.md`](docs/architecture.md) for the
> full roadmap.

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

This opens a window where you can select a photo, mark the four
rectification corners (defaults to the full image bounds — adjust them
to the actual wall plane), optionally enable scale calibration, and click
**Generate Drawing** to produce a `.png` preview and a layered `.dxf`.
Corner/calibration input is numeric for now (spin boxes), not yet an
interactive click-on-the-photo canvas — see the roadmap.

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

## Packaging (sharing a build with someone else)

**This only produces a real, runnable Windows build when run on an
actual Windows machine.** PyInstaller packages for whatever OS it's
running on — it does not cross-compile. If you're building from a
non-Windows dev environment, `pyinstaller packaging/app.spec` will still
run and is useful for validating the spec itself (it's how this spec was
developed and tested), but the resulting binary won't run on Windows.

### The simple path: sharing with one or two people

You don't need an installer or a code-signing certificate just to hand
this to a colleague.

**1. Freeze the app:**

```powershell
pyinstaller packaging\app.spec --distpath packaging\dist --workpath packaging\build --noconfirm
```

Produces `packaging\dist\PhotoToCAD\` — `PhotoToCAD.exe` plus an
`_internal\` folder containing the Qt runtime, OpenCV, the Python
interpreter, and the bundled `i18n\`/`models\` data. The person you send
this to needs nothing else installed; everything is in that folder.
Smoke-test it yourself first: run `PhotoToCAD.exe` directly and confirm
the window opens and a real photo produces real output.

**2. Zip the whole `PhotoToCAD` folder** (not just the `.exe` — it needs
`_internal` sitting next to it) and send the zip. Expect a few hundred MB
compressed; use a file-transfer link (WeTransfer, Drive, OneDrive) rather
than email if there's a size limit.

**3. What the other person will see:** the first time they double-click
`PhotoToCAD.exe`, Windows will very likely show *"Windows protected your
PC — Microsoft Defender SmartScreen prevented an unrecognized app from
starting."* This is normal for any fresh, unsigned executable — it isn't
a sign anything is broken. They click **More info → Run anyway** once;
Windows remembers after that. Worth telling them in advance so it doesn't
look alarming.

### The fuller path: a proper installer, for broader distribution

If you're distributing this beyond a handful of people, or the
SmartScreen prompt above is a dealbreaker, there's a real Inno Setup
installer and a signing script already written:

- **Compile the installer:** open `packaging\installer.iss` in the Inno
  Setup IDE (or run `ISCC.exe packaging\installer.iss`). Produces
  `packaging\installer_output\PhotoToCAD-Setup-<version>.exe` with a
  Start Menu entry, optional desktop shortcut, and uninstaller.
- **Sign both executables:** `powershell -ExecutionPolicy Bypass -File
  packaging\sign.ps1`, after filling in your actual certificate
  path/password (see the script's own header comment). Note that as of
  a 2024 SmartScreen policy change, signing — even with a paid EV
  certificate — no longer grants instant trust; reputation still builds
  via download volume either way. Signing mainly helps by turning a hard
  SmartScreen block into a one-click-through warning, and by giving
  antivirus engines a stable publisher identity to whitelist instead of
  a new file hash on every build. If you want zero SmartScreen friction
  from day one without buying a certificate, look into
  [Microsoft Trusted Signing](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options)
  (~$10/month, individual developers in the US/Canada) or
  [SignPath Foundation](https://signpath.org/) (free for qualifying open
  source projects).

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
packaging/          app.spec (PyInstaller), installer.iss (Inno Setup),
                    sign.ps1 (Authenticode) — see "Packaging" above
docs/               architecture.md and future ADRs
```

## License

MIT — see [`LICENSE`](LICENSE).