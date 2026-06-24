"""Shared pytest fixtures/config.

Forces Qt's offscreen platform plugin so the test suite runs headless
(CI, this sandbox, etc.) without a real display.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
