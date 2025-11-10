import re
from typing import Generator
import tempfile
import filecmp
import os
import sys
import shlex
from rich import get_console
from rich.text import Text
from curvpyutils.shellutils import print_delta
from .util import StrListWithMostCommon

patterns = {
    "start_subst": re.compile(r"@subst\[`(.*)`\]"),
    "end_subst": re.compile(r"@endsubst"),
    "indent": re.compile(r"^(\s*)")
}

class ReplacementCmd:
    def __init__(self, cmd: str, extra_args: list[str], extra_args_leading: list[str]):
        # Expand environment variables before splitting into command parts
        cmd = os.path.expandvars(cmd)
        try:
            cmd_parts = shlex.split(cmd, posix=True)
        except ValueError:
            cmd_parts = cmd.split()
        self.cmd = cmd_parts[0] if len(cmd_parts) > 0 else ""
        self.args = cmd_parts[1:] if len(cmd_parts) > 1 else []
        if extra_args_leading is not None and len(extra_args_leading) > 0:
            self.args.extend(extra_args_leading)
        if extra_args is not None and len(extra_args) > 0:
            self.args.extend(extra_args)
            
    def to_text(self) -> Text:
        return Text.assemble(
            (self.cmd, "bold yellow"),
            (f" {(' '.join(self.args))}", "bold yellow"),
        )

    def __str__(self):
        return self.to_text().__str__()
    
    def __repr__(self):
        return f"ReplacementCmd({self.__str__()})"

    def invoke(self) -> list[str]:
        """
        Invokes the replacement command with the given arguments.
        """    
        import subprocess
        res = subprocess.check_output([self.cmd, *self.args]).decode("utf-8")
        res_lines = res.split("\n")
        if res_lines[-1].strip() == "":
            res_lines = res_lines[:-1]
        ret_arr = [f"{line}\n" for line in res_lines]
        return ret_arr

class SubstBlock:
    def __init__(self, start_line_num: int, end_line_num: int, replacement_cmd: ReplacementCmd):
        self.start_line_num = start_line_num
        self.end_line_num = end_line_num
        self.replacement_cmd = replacement_cmd
    

    def to_text(self) -> Text:
        t = Text.assemble(
            ("SubstBlock", "purple"),
            ("(from line ", ""),
            (str(self.start_line_num), "bold yellow"),
            (" to ", ""),
            (str(self.end_line_num), "bold yellow"),
            (")", ""),
            (" with replacement command [", ""),
            self.replacement_cmd.to_text(),
            ("]", ""),
        )
        return t

    def __str__(self):
        return f"SubstBlock(from line {self.start_line_num} to {self.end_line_num} with replacement command `{str(self.replacement_cmd)}`)"
    
    def invoke_replacement_cmd(self) -> list[str]:
        return self.replacement_cmd.invoke()

def find_subst_blocks_iter(file_path: str, extra_args: list[str], extra_args_leading: list[str]) -> Generator[SubstBlock, None, None]:
    with open(file_path, "r") as file:
        lines = file.readlines()
    in_subst_block = False
    start_line_num = None
    end_line_num = None
    for line_num, line in enumerate(lines):
        # Use re.search to find the pattern anywhere in the line.
        match = patterns["start_subst"].search(line)
        if match:
            in_subst_block = True
            start_line_num = line_num
            replacement_cmd = ReplacementCmd(match.group(1), extra_args=extra_args, extra_args_leading=extra_args_leading)
        if in_subst_block:
            # Use re.search to find the pattern anywhere in the line.
            match = patterns["end_subst"].search(line)
            if match:
                in_subst_block = False
                end_line_num = line_num
                yield SubstBlock(start_line_num, end_line_num, replacement_cmd)

def get_most_common_indent_str(lines_being_replaced: list[str]) -> str:
    """
    Returns a StrListWithMostCommon of the indent strings in the lines being replaced.
    """
    indent_strs:StrListWithMostCommon = StrListWithMostCommon()
    for line in lines_being_replaced:
        try:
            indent_strs.append(patterns["indent"].match(line).group(1))
        except:
            pass
    return str(indent_strs)

def replace_subst_block(filename: str, output_filename: str, verbose: int = 0, extra_args: list[str] = [], extra_args_leading: list[str] = []):
    """
    Replaces the subst block with the replacement lines.
    """
    if verbose > 1:
        print(f"replace_subst_block: filename={filename}, output_filename={output_filename}")
    with open(filename, "r") as file:
        lines = file.readlines()
    output_lines = []
    last_line_written_out = 0
    for subst_block in find_subst_blocks_iter(filename, extra_args=extra_args, extra_args_leading=extra_args_leading):
        if verbose > 1:
            get_console().print("replace_subst_block: found subst block ", subst_block.to_text())
        replacement_lines = subst_block.invoke_replacement_cmd()
        indentation_str = get_most_common_indent_str(lines[subst_block.start_line_num:subst_block.end_line_num + 1])
        for line in lines[last_line_written_out:subst_block.start_line_num+1]:
            output_lines.append(line)
        for line in replacement_lines:
            output_lines.append(indentation_str + line)
        output_lines.append(lines[subst_block.end_line_num])
        last_line_written_out = subst_block.end_line_num+1
    for line in lines[last_line_written_out:]:
        output_lines.append(line)
    with open(output_filename, "w") as file:
        file.writelines(output_lines)

def run_substitution_on_file(file_path: str, dry_run: bool = False, verbose: int = 0, force: bool = False, disable_colors: bool = False, extra_args: list[str] = [], extra_args_leading: list[str] = [], debug_output_dir: str|None = None) -> bool:
    """
    Runs substitution on a single file, with prompting and a preview diff.

    Returns True if the file was modified, False otherwise.
    """

    file_modified = False

    try:
        temp_out_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        if verbose > 1:
            get_console().print(f"run_substitution_on_file: file_path=[yellow]{file_path}[/yellow], temp_out_file.name=[yellow]{temp_out_file.name}[/yellow]")
        replace_subst_block(file_path, temp_out_file.name, verbose=verbose, extra_args=extra_args, extra_args_leading=extra_args_leading)
        temp_out_file.close()

        # Compare files byte by byte to see if they differ
        if filecmp.cmp(file_path, temp_out_file.name, shallow=False):
            if verbose > 1:
                get_console().print(f"no changes needed for [yellow]{file_path}[/yellow]")
        else:
            if dry_run or not force:
                # show the delta
                print_delta(file_path, temp_out_file.name)

            # prompt for confirmation before overwriting
            if not dry_run:
                if not force:
                    response = input("Overwrite original file with changes? [y/N] ")
                    if response.lower() != 'y':
                        get_console().print(f"aborting - no changes made for [yellow]{file_path}[/yellow]")
                        return False
                if debug_output_dir is not None:
                    os.makedirs(debug_output_dir, exist_ok=True)
                    os.rename(temp_out_file.name, os.path.join(debug_output_dir, os.path.basename(file_path)))
                else:
                    os.rename(temp_out_file.name, file_path)
                file_modified = True
            else:
                # if it is a dry run, don't overwrite anything
                if debug_output_dir is not None:
                    os.makedirs(debug_output_dir, exist_ok=True)
                    os.rename(temp_out_file.name, os.path.join(debug_output_dir, os.path.basename(file_path)))
                    if verbose > 1:
                        get_console().print(f"replace_subst_block: dry run, not overwriting file {file_path}, but writing to {os.path.join(debug_output_dir, os.path.basename(file_path))}")
                else:
                    if verbose > 1:
                        get_console().print(f"replace_subst_block: dry run, not overwriting file {file_path}")
    except Exception as e:
        get_console().print(f"error (at line {sys.exc_info()[2].tb_lineno}): {e}")
        raise e
    finally:
        if os.path.exists(temp_out_file.name):
            os.unlink(temp_out_file.name)
    return file_modified
