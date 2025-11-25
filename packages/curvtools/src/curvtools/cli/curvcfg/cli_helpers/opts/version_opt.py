import click
from curvtools.cli.curvcfg.version import get_styled_version, get_styled_version_message, get_package_name, get_program_name

def version_opt() -> click.Option:
    return click.version_option(
        version=get_styled_version(),
        message=get_styled_version_message(),
        prog_name=get_program_name(),
        package_name=get_package_name(),
    )
