import click
from importlib import metadata as ilmd
from curvtools import get_curvtools_version_str
from curvtools.cli.curvcfg.settings import PROGRAM_NAME, PACKAGE_NAME

def _dist_name_for_this_package() -> str:
    try:
        top = __package__.split('.')[0]
        return ilmd.packages_distributions().get(top, [top])[0]
    except Exception:
        return PACKAGE_NAME

def get_urls() -> dict[str, str]:
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

def get_styled_version(prepend_v: bool = False) -> str:
    """
    Return styled version for click.version_option.
    """
    version = get_curvtools_version_str(short_version=True)
    version_styled = click.style(f"{'v' if prepend_v else ''}{version}", fg="bright_yellow")
    return version_styled

def _strip_github_url(url: str) -> str:
    """
    Strip the https prefix and any suffix from a GitHub URL.
    """
    url = url.replace("https://", "")
    url = url.replace(".git", "")
    url = url.rstrip("/")
    return url

def get_styled_version_message() -> str:
    """
    Return styled version message for click.version_option.
    Based on URLs in pyproject.toml's [project.urls] section.
    """
    version_styled = f" {get_styled_version(prepend_v=True)} "

    # get styled program name and version
    program_name_styled = click.style(PROGRAM_NAME, fg="bright_yellow")

    # get styled github URL
    github_url = get_urls().get("repository", "https://github.com/curvcpu/curv")
    github_url_styled = click.style(_strip_github_url(github_url), fg="cyan")
    
    message = program_name_styled + \
        version_styled + \
        f"- Curv RISC-V CPU build config tool (" + \
        github_url_styled + \
        ")"
    return message

def get_package_name() -> str:
    return _dist_name_for_this_package()

def get_program_name() -> str:
    return PROGRAM_NAME