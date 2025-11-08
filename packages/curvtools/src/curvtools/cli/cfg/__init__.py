from importlib import metadata as ilmd
from curvtools.version import get_version_str

# Re-export CLI entry for project.scripts
from .cli import main  # noqa: F401

def _dist_name_for_this_package() -> str:
    # Avoid hard-coding the distribution name when it differs from the module
    top = __package__.split('.')[0]
    return ilmd.packages_distributions().get(top, [top])[0]

def get_version() -> str:
    """Return curvtools package version using the shared version API.

    Short version string is used to match other tools in this repo.
    """
    return get_version_str(short_version=True)

def get_package_name() -> str:
    _DIST = _dist_name_for_this_package()
    try:
        return ilmd.metadata(_DIST).get("name", "")
    except Exception:
        return ""

def get_urls() -> dict[str, str]:
    """Return mapping of Project-URL keys to URLs from package metadata."""
    urls: dict[str, str] = {}
    _DIST = _dist_name_for_this_package()
    try:
        meta = ilmd.metadata(_DIST)
    except Exception:
        return urls
    for key, value in meta.items():
        if key.startswith("Project-URL"):
            url_key, url_value = value.split(",", 1)
            urls[url_key.strip()] = url_value.strip()
    return urls
