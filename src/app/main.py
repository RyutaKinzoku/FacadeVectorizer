"""Application entry point.

Deliberately minimal for this first commit: it proves the PySide6 +
packaging skeleton runs end-to-end (see docs/architecture.md, "stand up
the packaging skeleton early"). Pipeline wiring lands in app.composition
once the domain model and stage Protocols are locked.

Every user-facing string goes through self.tr(...) from day one, per the
internationalisation plan (English / Spanish via Qt .ts/.qm files).
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QLocale, QTranslator
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(self.tr("Photo to CAD"))
        self.setCentralWidget(
            QLabel(self.tr("Photo \u2192 Architectural Drawing — project skeleton."))
        )
        self.resize(480, 240)


def _install_translator(app: QApplication) -> QTranslator:
    """Load the compiled translation matching the system locale.

    Falls back silently to English (the source language, no .qm needed)
    if no matching .qm is found under i18n/ — e.g. before any translations
    have been compiled yet, as in this first commit.
    """
    translator = QTranslator()
    locale = QLocale.system().name()  # e.g. "es_ES"
    translator.load(f"app_{locale[:2]}", "i18n")
    app.installTranslator(translator)
    return translator


def main() -> int:
    app = QApplication(sys.argv)
    translator = _install_translator(app)  # noqa: F841 — keep alive for app lifetime

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
