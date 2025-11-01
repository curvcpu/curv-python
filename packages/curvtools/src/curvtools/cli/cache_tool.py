import click

@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--plus-one", type=int, help="Add one to the argument and print the result"
)
def main(plus_one: int | None) -> None:
    """Curv cache tool."""
    if plus_one is not None:
        click.echo(str(plus_one + 1))
