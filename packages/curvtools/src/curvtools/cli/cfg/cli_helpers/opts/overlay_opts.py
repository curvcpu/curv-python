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
    overlay_toml_base_name_opt = click.option(
        "--overlay-toml-base-name",
        "overlay_toml_base_name",
        metavar="<overlay-toml-base-name>",
        default="overlay.toml",
        show_default=True,
        help="Base name of overlay TOML files, e.g., 'overlay.toml' or 'dev1.overlay.toml' when using prefixes.",
    )
    overlay_prefix_opt = click.option(
        "--overlay-prefix",
        "overlay_prefix",
        metavar="<overlay-prefix>",
        default="",
        show_default=True,
        help="Prefix to select between prefixed overlay TOML files (e.g., 'dev1' selects 'dev1.overlay.toml' and 'overlay.toml')",
    )
    no_combine_overlays_opt = click.option(
        "--combine-overlays/--no-combine-overlays",
        "combine_overlays",
        is_flag=True,
        default=True,
        help="If both <prefix>.overlay.toml and overlay.toml exist, we normally apply both with the prefixed file taking precedence. This option disables that behavior and uses the prefixed file only when both are present.",
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

    opts = [overlay_dir_opt, overlay_toml_base_name_opt, overlay_prefix_opt, no_combine_overlays_opt, no_ascend_dir_hierarchy_opt]
    
    # Apply in reverse so the first listed ends up nearest the function
    def _wrap(f):
        for opt in reversed(opts):
            f = opt(f)
        return f
    
    return _wrap
