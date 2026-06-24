# **ORTHOGON** — Photo → Architectural Drawing (On-Premise, Free, Python)

Development plan for **Orthogon**, a Windows desktop application that takes a single
photograph of a building façade and produces a clean line drawing exported as **.png**
(raster preview) and **.dxf** (editable, layered vectors for AutoCAD / Rhino), with
perspective correction so that photos shot from a bad angle can still be used. Built in
**Python**, shipped as a **signed Windows installer** that runs fully offline.

*Name rationale:* "Orthogon" combines *ortho-* (orthographic projection, the goal of
rectification) and *-gon* (geometry), emphasizing perspective correction and clean
geometric output. Brief, memorable, architecture-friendly, and pronunciation-agnostic
across English/Spanish.

---

## 1. Honest feasibility framing (read this first)

Before any architecture, three realities should shape expectations and scope:

1. **You cannot recover true scale from one photo.** A single image has no absolute
   size information. The "scaled" requirement is only achievable if the user supplies
   one known real-world dimension (e.g. door height = 2.10 m) or a scale reference in
   the shot. The app must include a **calibration step**; everything downstream is
   scaled from that one input.

2. **Bad-angle correction works well for flat façades, not miracles.** Rectifying an
   upward/oblique shot into a fronto-parallel elevation is solvable for planar walls
   with strong straight edges (vanishing-point homography). Extreme angles, heavy
   occlusion (wires, plants, the balcony in your photo), or curved surfaces degrade
   badly. Plan for a manual fallback (user drags 4 corner points).

3. **The clean, idealised drawing in your second image is a *target*, not a literal
   auto-output.** That drawing is symmetric, straightened, and regularised — it implies
   semantic understanding plus geometric "tidying." A realistic local tool produces a
   faithful vector *draft* that is **"ready for CAD cleanup"** (your exact phrasing).
   Full regularisation to that pristine state is a later, ML-heavy phase.

Designing around these three points keeps the project credible and the users happy.

---

## 2. Technology stack (Python, all free, all offline)

Keep two dependency sets separate: a **slim runtime set** that gets shipped in the
installer, and a **dev-only set** that never reaches the user (keeps the installer
small and the attack surface low).

**Runtime (shipped in the installer)**

| Concern | Choice | Licence |
|---|---|---|
| Language / runtime | Python 3.12 (frozen, user installs nothing) | PSF |
| GUI | PySide6 (Qt for Python) — mature desktop, signals/slots, canvas | LGPL |
| Classic computer vision | `opencv-contrib-python` (incl. `ximgproc` FastLineDetector) | Apache-2.0 |
| ML inference | `onnxruntime` (CPU; DirectML/CUDA optional) | MIT |
| Image I/O | `Pillow`, `numpy` | MIT-CMU / BSD |
| Geometry ops | `shapely` (merge/snap/simplify lines) | BSD |
| DXF export | `ezdxf` | MIT |

**Dev-only (training/tooling — NOT shipped)**

| Concern | Choice |
|---|---|
| Model training / export-to-ONNX | `PyTorch` (export models, then ship only `.onnx`) |
| Tests | `pytest`, `pytest-qt` |
| Lint / format / types | `ruff`, `mypy` |
| Security / supply chain | `pip-audit`, `cyclonedx-py` (SBOM), `pip-tools` (locked pins) |
| Packaging | `PyInstaller` → `Inno Setup` (installer) → `signtool` (signing) |

> **Why ship ONNX, not PyTorch:** `onnxruntime` is a fraction of the size of full
> PyTorch and avoids shipping a training framework to end users. Train/fine-tune with
> PyTorch in dev, export to `.onnx`, ship only the `.onnx` files. This also dodges the
> pickle security problem (see §6).

**Licence/patent watch-out:** OpenCV's classic `LineSegmentDetector` was removed over a
licence issue; use **FastLineDetector** (`ximgproc`) or EDLines. PySide6 is **LGPL** —
fine for a freely distributed app, but keep it a dynamically-linked dependency (which
PyInstaller does by default) and don't statically modify Qt. Verify every dependency's
licence before release — "free" is a hard requirement here.

---

## 3. The processing pipeline (the heart of the app)

Model the work as an explicit, ordered pipeline of single-purpose stages. Each stage has
a narrow interface, is independently testable, and is swappable.

```
Photo
  → [1] Ingest & validate        (safe decode, size/pixel limits, no EXIF trust)
  → [2] Pre-process              (denoise, contrast, undistort if lens data)
  → [3] Rectify                  (auto vanishing-point homography OR manual 4-point)
  → [4] Calibrate scale          (user enters one known dimension)
  → [5] Edge / line extraction   (Canny + FastLineDetector, or HED/DexiNed/PiDiNet ONNX)
  → [6] (later) Semantic parse   (segment windows/doors/balcony/ornament)
  → [7] Vectorise                (segments → polylines/arcs; merge collinear via shapely)
  → [8] Regularise (optional)    (straighten, snap to 0/90°, enforce symmetry/grid)
  → [9] Assemble drawing model   (geometry on semantic layers, real units)
  → [10] Export                  (PNG render + DXF via ezdxf)
```

Stages 3, 5, 6, 8 are where "intelligence" lives. Build 1–5, 7, 9, 10 first (a working
MVP), then add 6 and 8.

### Key algorithm notes
- **Rectification:** detect dominant line directions (Hough / FastLineDetector) → estimate
  two vanishing points → compute the rectifying homography (`cv2.findHomography` /
  `warpPerspective`) → fronto-parallel view. Always offer manual 4-corner drag as fallback
  and override.
- **Edge extraction:** start classic (bilateral filter → `cv2.Canny` → FastLineDetector).
  Upgrade to a learned edge model — **PiDiNet** is lightweight and CPU-friendly;
  **DexiNed/HED** are cleaner but heavier — exported to ONNX, run via `onnxruntime`.
- **Vectorisation:** FastLineDetector already yields segments; lift them to world
  coordinates, then use **shapely** to merge collinear/near-duplicate segments, snap
  angles to 0/90° (and the dominant skew), and join endpoints within a tolerance. For
  filled silhouettes, a potrace-style trace (`pypotrace`) is an option.
- **Semantic parsing (Phase 3):** a façade segmentation model (fine-tune on **CMP Façade**,
  **ECP**, or **eTRIMS** datasets in PyTorch, export to ONNX) labels wall/window/door/
  balcony/cornice → enables per-layer DXF and regularisation of repeated windows.

### DXF output specifics (`ezdxf`)
Write real-world units (mm or m), model space, and **separate layers** per semantic class
(`WALLS`, `OPENINGS`, `WINDOWS`, `DOORS`, `BALCONY`, `ORNAMENT`, `GUIDES`). Use
`LWPOLYLINE` / `LINE` / `ARC` entities. Layered, scaled output is exactly what makes it
usable in AutoCAD and Rhino.

---

## 4. SOLID-aligned architecture (Pythonic)

Layered/clean architecture; dependencies point inward toward abstractions. In Python,
"interfaces" are `typing.Protocol` (or `abc.ABC`); wiring is plain **constructor
injection** assembled in one composition root — no framework needed.

```
ui/            PySide6 widgets, view-models, canvas; talks to application via use-cases
application/   pipeline orchestrator, use-cases, undo/redo; depends only on Protocols
domain/        DrawingModel, Layer, Stroke, ScaleCalibration (dataclasses, value objects)
infrastructure/  adapters: opencv, onnxruntime, ezdxf, filesystem
composition.py   the only place concrete classes are wired to Protocols (DI root)
```

**Protocol set (each small and focused — ISP):**
`ImageValidator`, `Preprocessor`, `Rectifier`, `ScaleCalibrator`, `EdgeDetector`,
`FacadeSegmenter`, `Vectorizer`, `GeometryRegularizer`, `DrawingExporter`
(implemented twice: PNG and DXF).

**SOLID mapping**
- **S — Single responsibility:** one class per pipeline stage; the DXF exporter only writes DXF.
- **O — Open/closed:** add a new edge detector or exporter by adding a class, never editing the pipeline.
- **L — Liskov:** every `EdgeDetector` is interchangeable; the orchestrator never special-cases one.
- **I — Interface segregation:** the small Protocols above instead of one fat `ImageProcessor`.
- **D — Dependency inversion:** the application layer imports only from `domain`/Protocols;
  concrete `cv2` / `onnxruntime` / `ezdxf` live behind **adapter** classes and are injected
  at the composition root. This keeps the CV/ML core unit-testable with fakes and stops
  third-party APIs leaking through the codebase.

---

## 5. Design patterns (where each earns its place)

- **Pipeline / Chain of Responsibility** — the stage sequence in §3; each stage processes a
  shared context object and passes it on. Stages reorderable/skippable via config.
- **Strategy** — swappable algorithm per stage (Canny vs PiDiNet edges; auto vs manual
  rectify), expressed as alternative Protocol implementations. The core "works even at a
  bad angle" knob.
- **Factory** — build the right strategy/exporter from user settings.
- **Adapter** — wrap `cv2`, `onnxruntime`, `ezdxf` behind your own Protocols (DIP).
- **Builder** — assemble the layered DXF document step by step.
- **Command + Memento** — every cleanup edit (move/delete/snap a line) is a command with
  undo/redo state; essential for an editable canvas.
- **Observer** — Qt **signals/slots** for live preview as parameters change (Python's
  natural replacement for MVVM data-binding).
- **Repository** — load/save a "project" (source photo + calibration + edits + settings).

---

## 6. Internationalisation — English / Spanish

The UI must be selectable between **English** and **Spanish**, with room to add more
languages later without code changes (an Open/Closed concern: adding a language = adding a
translation file, never editing logic).

**Mechanism — Qt's translation system (built into PySide6).**
- Wrap every user-facing string in `self.tr("...")` instead of hard-coding it. Keep strings
  out of the domain/application layers — only the `ui/` layer is translated; pipeline/log
  messages stay in a single base language.
- Extract strings with `pyside6-lupdate` into `.ts` files (`app_en.ts`, `app_es.ts`),
  translate them (Qt Linguist), and compile to binary `.qm` with `pyside6-lrelease`.
- At runtime, load the chosen language with a `QTranslator` (`installTranslator`). Wrap this
  behind a small `LocalizationService` (a Strategy/Facade) so the rest of the UI just calls
  `set_language("es")` and never touches Qt translation APIs directly (DIP).

**Language selection & persistence.**
- Default to the OS locale via `QLocale.system()`, fall back to English if it isn't EN/ES.
- Expose a language switcher in Settings; persist the choice in the user config (alongside
  other project/app settings via the Repository). Apply live where practical, or prompt for
  restart if simpler.

**Things that are easy to forget (so note them now):**
- **Numbers, units, decimals** — the scale-calibration input and DXF dimensions must respect
  locale decimal separators (Spanish uses a comma). Parse/format via `QLocale`, store
  canonically (always a `.` internally), display localised.
- Keep `.qm` files out of compiled code — they're data, bundled by the installer (see §9).

---

## 7. OWASP / security (sharper for Python + a frozen app)

OWASP is web-centric, but several items map directly onto an offline Python image tool
that loads files, ships ML models, and is frozen into an executable.

- **Untrusted file input (A03-ish):** image files are an attack surface (decompression
  bombs, malformed headers). Set `Pillow.Image.MAX_IMAGE_PIXELS`, enforce max file size
  and pixel dimensions, decode defensively, and never trust EXIF.
- **Pickle / deserialization = remote code execution (A08) — the big one in Python.**
  `torch.load`, `numpy.load(allow_pickle=True)`, and `pickle` all execute arbitrary code on
  load. **Ship and load models as ONNX (or safetensors) only; never load a `.pt`/pickle at
  runtime.** Verify every shipped model with a **SHA-256 checksum** at startup (and a
  signature if you can).
- **Vulnerable/outdated components (A06):** OpenCV, Pillow, onnxruntime have had CVEs. Pin
  with `pip-tools` (locked hashes), run `pip-audit` in CI, ship an **SBOM** (`cyclonedx-py`),
  patch promptly.
- **Injection / unsafe dynamic code (A03):** never `eval`/`exec` file content; if you ever
  spawn a subprocess, pass an argument list, never a composed shell string.
- **Path traversal:** use `pathlib`, `.resolve()`, and confine project/load/save paths to
  expected directories.
- **Security misconfiguration / least privilege (A05):** runs as a normal user, no admin;
  install per-user or to Program Files via the installer; write only to user/temp dirs and
  clean temp files up.
- **Frozen-app integrity & updates:** code-sign the `.exe` and the installer (see §8);
  PyInstaller binaries frequently trip antivirus heuristics — **signing + build
  reproducibility + reputation** is the mitigation. Ship signed updates only.
- **Logging (A09):** log errors without leaking file contents or full user paths.

Because the product is fully on-premise with no network calls in normal use, the real
attack surface is small: **malicious input images** and the **ML-model supply chain**.
Concentrate effort there.

---

## 8. Phased roadmap

- **Phase 0 — Spike (1–2 wks):** prove the concept on ~10 real photos in a notebook: manual
  4-point rectify → Canny+FastLineDetector → shapely merge → `ezdxf` DXF. Confirms the
  approach before building the app shell.
- **Phase 1 — MVP:** clean architecture + composition root; ingest/validate; manual
  rectification; scale-by-known-dimension; classic edge+vectorise; PNG + layered DXF export;
  project save; PySide6 UI **wired for translation from the start (English + Spanish via Qt
  `.ts`/`.qm`)** — retrofitting i18n later is far more painful than building it in now.
- **Phase 2 — Smarter input:** automatic vanishing-point rectification with manual override;
  learned edge detection (PiDiNet ONNX); collinear merge + ortho snap + endpoint join.
- **Phase 3 — Semantic understanding:** façade segmentation model (windows/doors/balcony/
  ornament) → per-layer DXF + regularisation of repeated elements and symmetry.
- **Phase 4 — Editing UX:** interactive canvas with command/undo-redo, snapping, layer
  toggles, per-element nudging — the "cleanup" workspace.
- **Phase 5 — Package & ship:** `pip-audit` + SBOM, model-hash verification, **PyInstaller
  freeze → Inno Setup installer → code signing** (full detail in §8).

---

## 9. Building the Windows installer (Phase 5, in detail)

Three stages: freeze → wrap → sign.

**1. Freeze the app with PyInstaller.**
- Prefer **one-folder** mode (`--onedir`) over one-file: faster startup, easier to bundle
  the `.onnx` models and Qt plugins, fewer AV false positives. (One-file is simpler to hand
  around but unpacks to temp on every launch.)
- Add the models and any resources as data: `--add-data "models;models"`, **and the compiled
  translations `--add-data "i18n;i18n"` (the `.qm` files)**, while excluding the dev-only
  world (`--exclude-module torch`, tests, etc.) to keep size down.
- Collect PySide6 properly (PyInstaller has a Qt hook, but verify the `platforms` plugin and
  `QtWebEngine` if used are included). Use a committed `orthogon.spec` file rather than a long CLI so
  the build is reproducible.
- Smoke-test the frozen output on a clean Windows VM with **no Python installed** — this is
  where missing plugins/DLLs surface.

**2. Wrap it in a Windows installer with Inno Setup (free).**
- Inno Setup script (`installer.iss`) takes the PyInstaller `dist/` folder and produces a single
  `Orthogon-setup.exe`: installs to Program Files (or per-user), creates Start Menu / desktop
  shortcuts, registers an uninstaller, associates `.orthogon` project files, and configures the
  uninstaller.
- Bundle the `models/` + their `.sha256` files; the app verifies hashes on first run.
- Alternatives if you prefer: **NSIS** (similar, free), or **Briefcase** (BeeWare) which can
  emit an MSI/MSIX directly and integrates packaging into the Python toolchain.

**3. Code-sign the executable and the installer.**
- Sign both `Orthogon.exe` and `Orthogon-setup.exe` with `signtool` (Authenticode) using a
  code-signing certificate. This is what tames Windows SmartScreen and most AV false positives
  that PyInstaller binaries attract. Without signing, expect "unknown publisher" warnings.

**Automate it in CI:** a pipeline that runs `ruff`/`mypy` → `pytest` → `pip-audit` →
`cyclonedx-py` (SBOM) → PyInstaller → Inno Setup → `signtool`, producing a signed
`Orthogon-setup.exe` as the build artifact.

---

## 10. Suggested repository layout

```
/src/orthogon
  /ui              (PySide6 widgets, view-models, editing canvas)
  /application     (use-cases, pipeline orchestrator, Protocols, undo/redo)
  /domain          (DrawingModel, Layer, Stroke, ScaleCalibration, value objects)
  /infrastructure
     /vision       (opencv adapters: rectify, edges, vectorise)
     /ml           (onnxruntime adapters; model load + SHA-256 verification)
     /export       (PNG + ezdxf exporters)
     /persistence  (project repository)
  composition.py   (DI composition root — wires concretes to Protocols)
/models            (*.onnx + *.sha256 — never pickle)
/i18n              (app_en.ts, app_es.ts source + compiled app_en.qm, app_es.qm)
/tests             (/unit /integration /fixtures(sample photos))
/packaging         (orthogon.spec for PyInstaller, installer.iss for Inno Setup, sign.ps1)
/docs              (threat-model.md, architecture.md, ADRs)
requirements.in / requirements.txt   (locked, hashed pins via pip-tools)
```

---

## 11. First three concrete steps

1. Run the **Phase 0 spike** end-to-end on your Maltese-townhouse photo (manual rectify +
   classic edges + shapely + ezdxf) to see how far you get before adding ML.
2. Lock the **domain model** (`DrawingModel`/`Layer`/`Stroke`/`ScaleCalibration`) and the
   stage **Protocols** — that decision drives SOLID compliance everywhere else.
3. Stand up the **packaging skeleton early** (a trivial PySide6 window → PyInstaller →
   Inno Setup → signed `setup.exe`) so "ships as an installer" is proven on day one, not
   discovered to be painful at the end.
