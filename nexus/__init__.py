from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("Nexus")
except PackageNotFoundError:
    __version__ = "unknown"
