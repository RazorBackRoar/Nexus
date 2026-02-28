"""Pytest configuration for Nexus tests."""

import os
import tempfile
from pathlib import Path


os.environ.setdefault(
    "HYPOTHESIS_STORAGE_DIRECTORY",
    str(Path(tempfile.gettempdir()) / "hypothesis-examples"),
)

try:
    from hypothesis import settings
except ModuleNotFoundError:
    settings = None


# Disable Hypothesis example DB writes to avoid creating local .hypothesis/
if settings is not None:
    settings.register_profile("no_local_db", database=None)
    settings.load_profile("no_local_db")
