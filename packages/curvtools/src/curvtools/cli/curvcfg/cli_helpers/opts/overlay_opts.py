import click

###############################################################################
#
# Common flags: overlay-related flags
#
###############################################################################

def overlay_opts():
    overlay_dir_opt = click.option(
        "--overlay-dir",
        "overlay_dir",
        metavar="<overlay-dir>",
        default=".",
        show_default=True,
        help="Lowest directory to look in for an overlay TOML file, after which we walk up the hierarchy.",
    ) 
    no_ascend_dir_hierarchy_opt = click.option(
        "--ascend-dir-hierarchy/--no-ascend-dir-hierarchy",
        "ascend_dir_hierarchy",
        is_flag=True,
        default=True,
        help=(
            "Do not ascend directories when searching for overlay toml files; "
            "only consider the overlay directory."
        ),
    )

    opts = [
        overlay_dir_opt, 
        no_ascend_dir_hierarchy_opt]
    
    # Apply in reverse so the first listed ends up nearest the function
    def _wrap(f):
        for opt in reversed(opts):
            f = opt(f)
        return f
    
    return _wrap
