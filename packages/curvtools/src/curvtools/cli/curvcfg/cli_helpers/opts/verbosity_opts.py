import click

###############################################################################
#
# common flags: --verbose/-v
#
###############################################################################
def verbosity_opts(include_verbose: bool):
    def cap3(ctx: click.Context, _param: click.Parameter, value: int) -> int: 
        ctx.ensure_object(dict)
        if "verbosity" not in ctx.obj:
            ctx.obj["verbosity"] = 0
        ctx.obj["verbosity"] = max(ctx.obj["verbosity"], min(value, 3))
        return ctx.obj["verbosity"]
    
    verbose_option = click.option(
        "--verbose", "-v",
        "verbose",
        count=True,
        help="Enables verbose mode. Repeat for more verbosity (up to -vvv).",
        callback=cap3,
    )
    opts = []
    opts.append(verbose_option) if include_verbose else None
    opts = [opt for opt in opts if opt is not None]

    # Apply in reverse so the first listed ends up nearest the function
    def _wrap(f):
        for opt in reversed(opts):
            f = opt(f)
        return f
    return _wrap
