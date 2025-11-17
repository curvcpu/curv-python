import click

###############################################################################
#
# Common flags: overlay-related flags
#
###############################################################################

def overlay_opts():
    overlay_path_list_opt = click.option(
        "--overlay-path",
        "overlay_path_list",
        metavar="<overlay-path1,overlay-path2,...>",
        default=[".", None],
        show_default=True,
        help=(
            "If specified once with a directory path, this is the lowest directory to look in for an overlay TOML file, after which we walk up the hierarchy. "
            "If specified one or more times with a file specific path, these files are treated as individual overlay files and there is no traversal of the directory hierarchy. It is an error to specify --overlay-path multiple times unless all are file paths."
        ),
        multiple=True
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
        overlay_path_list_opt, 
        no_ascend_dir_hierarchy_opt]
    
    # Apply in reverse so the first listed ends up nearest the function
    def _wrap(f):
        for opt in reversed(opts):
            f = opt(f)
        return f
    
    return _wrap
