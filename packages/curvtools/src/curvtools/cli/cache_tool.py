import click
from curvpyutils.adder.add import sum


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--plus-one", type=int, help="Add one to the argument and print the result"
)
def main(plus_one: int | None) -> None:
    """Curv cache tool."""
    if plus_one is not None:
        result = sum(plus_one, 1)
        click.echo(str(result))
