import click


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--profile", default="default", show_default=True, help="Config profile to use."
)
def main(profile: str) -> None:
    """Curv config tool."""
    click.echo(f"[curv-cfg] Using profile: {profile}")
