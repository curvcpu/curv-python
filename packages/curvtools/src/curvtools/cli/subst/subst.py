#!/usr/bin/env python3

import argparse
from dataclasses import dataclass
import os
import sys
import json
import shlex
from rich.text import Text
from rich import print, reconfigure, get_console

@dataclass
class SubInvocationItem:
    path: str
    args: argparse.Namespace

class SubInvocationItemList(list[SubInvocationItem]):
    def __init__(self, args: argparse.Namespace, json_data: list[dict]):
        super().__init__()
        self.args = args
        for item in json_data:
            path = item['path']
            args = item['args']
            args_arr:list[str] = []
            if args is not None:
                try:
                    if isinstance(args, str):
                        args_arr = shlex.split(args, posix=True)
                    else:
                        args_arr = args
                except ValueError:
                    args_arr = args
            # deep copy sys.argv[1:]
            combined_argv = sys.argv[1:].copy()
            combined_argv.extend(args_arr)
            combined_args = parse_args(combined_argv, override_paths=[path])
            self.append(SubInvocationItem(path=path, args=combined_args))

def parse_args(argv: list[str] = sys.argv[1:], override_paths: list[str] = None) -> argparse.Namespace:    
    class ColorReconfigureAction(argparse.BooleanOptionalAction):
        """
        BooleanOptionalAction that automatically reconfigures the default rich console to 
        disable colors if the "--no-colors" flag is used.  The option is then swallowed
        so it does not appear in the args Namespace after `args = parse_args(...)`
        """
        def __init__(self, option_strings, dest, **kwargs):
            # never create an attribute on the Namespace unless the flag appears,
            # and we’ll delete it anyway; default behavior is "colors on".
            kwargs.setdefault('default', argparse.SUPPRESS)
            super().__init__(option_strings, dest, **kwargs)

        def __call__(self, parser, namespace, values, option_string=None):
            # Treat '-C' as the negative form too.
            is_negative = (
                option_string in getattr(self, '_negative_option_strings', ())
            )

            if is_negative:
                # user asked to disable colors
                import os
                from rich import reconfigure
                os.environ["NO_COLOR"] = "1" # causes all calls to `c = Console()` to have colors off
                reconfigure(no_color=True)   # fallback to ensure default global rich console is replaced

            # swallow: remove the attribute so callers never see it
            vars(namespace).pop(self.dest, None)

    DEFAULT_EXTENSIONS = ['.sv', '.v', '.svh', '.vh']
    parser = argparse.ArgumentParser(description="Replace @subst...@endsubst blocks in a Verilog or SystemVerilog file")
    parser.add_argument("PATHS", nargs='+', type=str, help="File(s) or directory(ies) to process @subst blocks in; may be a single '@json:' prefixed filename with paths and args arrays inside it")
    file_opts = parser.add_argument_group("File Finding")
    file_opts.add_argument("--recursive", '-r', action="store_true", help="For directories in PATHS, whether to recurse into subdirectories")
    file_opts.add_argument("--extensions", '-e', nargs='+', default=DEFAULT_EXTENSIONS, type=str, help=f"File extensions to process within directories in PATHS (default: {', '.join(DEFAULT_EXTENSIONS)})")    
    control_opts = parser.add_argument_group("Control")
    control_opts.add_argument("--print-one-line", '-1', action="store_true", help="Print a single output line for each file processed (default: print nothing)")
    control_opts.add_argument("--force", '-f', action="store_true", help="Don't prompt for confirmation before overwriting a file (default: prompt for confirmation)")
    control_opts.add_argument("--colors", action=ColorReconfigureAction, help="Enable or disable colors in output (default: enabled)")
    control_opts.add_argument("--exit-code-if-modified", '-m', action="store_true", help="Exit with code 1 if any files were modified")
    debug_opts = parser.add_argument_group("Debugging")
    debug_opts.add_argument("--dry-run", action="store_true", help="Just show the diff, don't change any files")
    debug_opts.add_argument("--verbose", '-v', action="count", default=0, help="Show verbose output")
    debug_opts.add_argument("--debug-output-dir", '-o', action="store", default=None, help="Rather than in-place modifying the input file, write the output to same-named files in this directory")
    extra_args = parser.add_argument_group("Extra Arguments")
    extra_args.add_argument("--extra-args", '-x', action='append', nargs='*', type=str, help="Extra arguments to insert at the END of the script's argument list (can be specified multiple times)")
    extra_args.add_argument("--extra-args-leading", '-X', action='append', nargs='*', type=str, help="Extra arguments to insert at the BEGINNING of the script's argument list (can be specified multiple times)")
    args = parser.parse_args(argv)

    # if override_paths is not None, then we override the PATHS element with the given paths
    if override_paths is not None:
        args.PATHS = override_paths

    # Flatten the lists of lists that action='append' creates, or use empty list if none specified
    args.extra_args = [item for sublist in (args.extra_args or []) for item in sublist]
    args.extra_args_leading = [item for sublist in (args.extra_args_leading or []) for item in sublist]
    args.extensions = [ext if ext[0] == '.' else '.' + ext for ext in args.extensions]

    return args

def process_path(paths: list[str], extensions: list[str], recursive: bool, dry_run: bool, verbose: int, force: bool, extra_args: str, extra_args_leading: str, debug_output_dir: str|None, ret_paths_result: dict[str, bool] = dict[str, bool]()) -> None:
    """
    Processes a list of files or directories.

    Returns the paths_result dictionary.
    """
    for path in paths:
        if recursive and os.path.isdir(path):
            for root, dirs, _ in os.walk(path):
                for dir in dirs:
                    if verbose > 0:
                        print(f"Recursing into directory: {os.path.join(root, dir)}")
                    process_path([os.path.join(root, dir)], extensions, recursive, dry_run, verbose, force, extra_args, extra_args_leading, debug_output_dir, ret_paths_result)

        if os.path.isdir(path):
            if verbose > 0:
                print(f"Examining directory: {path}")
            for file in os.listdir(path):
                file_ext = os.path.splitext(file)[1]
                if verbose > 0:
                    print(f"Considering file: {os.path.join(path, file)} with extension '{file_ext}' against extensions: {extensions}")
                if any(file_ext == ext for ext in extensions):
                    if verbose > 0:
                        print(f"Recursing on file: {os.path.join(path, file)}")
                    process_path([os.path.join(path, file)], extensions, recursive, dry_run, verbose, force, extra_args, extra_args_leading, debug_output_dir, ret_paths_result)
                else:
                    if verbose > 0:
                        print(f"Skipping file: {os.path.join(path, file)}")
        else:
            if verbose > 0:
                print(f"Examining file: {path}")
            from .replace import run_substitution_on_file
            file_modified = run_substitution_on_file(file_path=path, dry_run=dry_run, verbose=verbose, force=force, extra_args=extra_args, extra_args_leading=extra_args_leading, debug_output_dir=debug_output_dir)
            ret_paths_result[path] = file_modified

def print_one_line_result(path: str, paths_result: dict[str, bool]) -> None:
    base_name = os.path.basename(path)
    if paths_result[path]:
        t = Text.assemble(
            "✔️ ",
                ("subst: " + base_name, "bold white"),
                (" (modified)", "bold yellow"),
            )
    else:
        t = Text.assemble(
            "✔️ ",
            ("subst: " + base_name + " (no change)", "dim"),
        )
    get_console().print(t)

def main():
    # Otherwise, normal operation
    args = parse_args()

    # collect the result of each path we process (True means file was modified, False means no change)
    ret_paths_result = dict[str, bool]()

    # If the PATHS element is prefixed with '@json:', then it is a JSON file with paths and args.
    # We re-invoke process_path for each element in the JSON array since each one
    # can have its own arguments
    if args.PATHS[0].startswith('@json:'):
        with open(args.PATHS[0][len('@json:'):], 'r') as f:
            json_data = json.load(f)
        args.PATHS = SubInvocationItemList(args, json_data)
        if isinstance(args.PATHS, SubInvocationItemList):
            for subinvocation_item in args.PATHS:
                process_path(paths=[subinvocation_item.path], 
                            extensions=args.extensions, 
                            recursive=args.recursive, 
                            dry_run=args.dry_run, 
                            verbose=args.verbose, 
                            force=args.force, 
                            extra_args=subinvocation_item.args.extra_args, 
                            extra_args_leading=subinvocation_item.args.extra_args_leading,
                            ret_paths_result=ret_paths_result,
                            debug_output_dir=args.debug_output_dir)
                print_one_line_result(subinvocation_item.path, ret_paths_result) if args.print_one_line else None
    else:
        for path in args.PATHS:
            process_path(paths=[path], 
                        extensions=args.extensions, 
                        recursive=args.recursive, 
                        dry_run=args.dry_run, 
                        verbose=args.verbose, 
                        force=args.force, 
                        extra_args=args.extra_args if args.extra_args is not None else "", 
                        extra_args_leading=args.extra_args_leading if args.extra_args_leading is not None else "", 
                        ret_paths_result=ret_paths_result,
                        debug_output_dir=args.debug_output_dir)
            print_one_line_result(path, ret_paths_result) if args.print_one_line else None

    if args.exit_code_if_modified and any(ret_paths_result.values()):
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()