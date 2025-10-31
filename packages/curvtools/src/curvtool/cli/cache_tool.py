import click


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--clear", is_flag=True, help="Clear the Curv build cache.")
def main(clear: bool) -> None:
    """Curv cache tool."""
    click.echo(f"[curv-cache-tool] clear={clear}")
