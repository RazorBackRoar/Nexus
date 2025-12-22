import importlib


def test_import_package():
    pkg = importlib.import_module("nexus")
    assert pkg is not None
