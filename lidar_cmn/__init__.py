from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("lidar-cmn")
except PackageNotFoundError:
    # Package not installed, e.g. run from the source folder
    __version__ = "unknown"
