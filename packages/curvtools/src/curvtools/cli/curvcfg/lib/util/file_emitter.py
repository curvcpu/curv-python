import os
import json
import re
from enum import Flag
from typing import Dict, Optional, Any, Iterable, List
from . import CfgValues, CfgValue
from pathlib import Path
from curvpyutils.file_utils import open_write_iff_change

class ConfigFileTypes(Flag):
    NONE = 0
    ENV = 1
    SVPKG = 2
    SVH = 4
    MAKEFILE = 8
    ALL = ENV | SVPKG | SVH | MAKEFILE

ConfigFileTypesForWriting = ConfigFileTypes.MAKEFILE | ConfigFileTypes.ENV | ConfigFileTypes.SVPKG | ConfigFileTypes.SVH

DEFAULT_OUTFILE_NAMES = {
    "makefile": "curv.mk",
    "env": ".curv.env",
    "svh": "curvcfg.svh",
    "svpkg": "curvcfgpkg.sv",
}


# def _emit_dep_file_contents(
#     merged_toml_name: Path,
#     build_dir: Path,
#     tomls_list: Iterable[Path],
#     curv_root_dir: Path,
#     verbosity: int = 0,
#     emit_files: ConfigFileTypes = ConfigFileTypesForWriting,
# ) -> str:
#     """
#     Generate the contents of a Makefile-style dependency fragment.

#     The resulting fragment expresses that each emitted config file produced under
#     <build_dir>/generated depends on:
#       - the merged TOML file under <build_dir>/config, and
#       - all of the source TOML files in tomls_list
    
#     IMPORTANT:  every path passed as an argument to this function must be both 
#     .is_absolute() and .resolve()'d by the caller.

#     All paths are expressed relative to $(CURV_ROOT_DIR) and $(BUILD_CONFIG_DIR)
#     in a GNU-make-compatible wrapped dependency rule.
#     """

#     curv_root_dir = Path(curv_root_dir).resolve()
#     toml_paths: List[Path] = [Path(p).resolve() for p in tomls_list]

#     # check our preconditions
#     assert (merged_toml_name.is_absolute()) and (str(merged_toml_name.resolve())==str(merged_toml_name)), "merged_toml_name must be an absolute path and already be resolved"
#     assert (build_dir.is_absolute()) and (str(build_dir.resolve())==str(build_dir)), "build_dir must be an absolute path and already be resolved"
#     assert all((p.is_absolute()) and (str(p.resolve())==str(p)) for p in toml_paths), "all toml paths must be absolute and already be resolved"

#     # Replace a path under CURV_ROOT_DIR with '$(CURV_ROOT_DIR)/<relpath>'
#     def repl_curv_root_dir(p: Path) -> str:
#         try:
#             rel = p.relative_to(curv_root_dir)
#             return "$(CURV_ROOT_DIR)/" + rel.as_posix()
#         except ValueError:
#             # Not under CURV_ROOT_DIR; leave as absolute path
#             return p.as_posix()

#     # Build list of targets to generate (relative to generated dir)
#     build_generated_dir_abs = (build_dir / "generated").resolve()
#     os.makedirs(build_generated_dir_abs, exist_ok=True)
#     build_generated_dir = repl_curv_root_dir(build_generated_dir_abs)

#     build_config_dir_abs = (build_dir / "config").resolve()
#     os.makedirs(build_config_dir_abs, exist_ok=True)
#     build_config_dir = repl_curv_root_dir(build_config_dir_abs)

#     # Determine which file types to include based on runtime flags
#     flag_to_key = {
#         ConfigFileTypes.MAKEFILE: "makefile",
#         ConfigFileTypes.ENV: "env",
#         ConfigFileTypes.SVPKG: "svpkg",
#         ConfigFileTypes.SVH: "svh",
#         ConfigFileTypes.JSON: "json",
#     }

#     target_names: List[str] = []
#     for flag, key in flag_to_key.items():
#         if emit_files & flag:
#             outname = DEFAULT_OUTFILE_NAMES.get(key)
#             if outname:
#                 target_names.append(outname)

#     # Targets to be generated
#     all_targets = target_names

#     lines: List[str] = []

#     # BUILD_GEN_DIR / BUILD_CONFIG_DIR assignments using $(CURV_ROOT_DIR)
#     lines.append(f"BUILD_GEN_DIR    := {build_generated_dir}")
#     lines.append("")
#     lines.append(f"BUILD_CONFIG_DIR := {build_config_dir}")
#     lines.append("")

#     # Dep fragment: replace build config dir with $(BUILD_CONFIG_DIR)
#     def repl_build_config_dir(p: Path) -> str:
#         try:
#             rel = p.relative_to(build_config_dir_abs)
#             return "$(BUILD_CONFIG_DIR)/" + rel.as_posix()
#         except ValueError:
#             return p.as_posix()

#     # Left-hand targets remain under BUILD_GEN_DIR
#     target_strs = " ".join(f"$(BUILD_GEN_DIR)/{name}" for name in all_targets)

#     # Build dependency list: output merged.toml and all input tomls
#     deps_list: List[str] = []
#     deps_list.append(
#         repl_build_config_dir(build_config_dir_abs / merged_toml_name.name)
#     )
#     deps_list.extend(repl_curv_root_dir(p) for p in toml_paths)

#     # Write wrapped dependency rule for readability (GNU make compatible)
#     lines.append(f"{target_strs}: \\")
#     for i, dep in enumerate(deps_list):
#         is_last = i == len(deps_list) - 1
#         if is_last:
#             lines.append(f"  {dep}")
#         else:
#             lines.append(f"  {dep} \\")

#     # Ensure trailing newline
#     return "\n".join(lines) + "\n"


# def _emit_dep_file(
#     path: Path,
#     contents: str,
#     write_only_if_changed: bool = True,
#     verbosity: int = 0,
# ) -> bool:
#     """
#     Write the dependency fragment file to *path*.

#     Returns True if the file was created or overwritten, False if it was left
#     unchanged because the contents were identical.
#     """
#     assert path.is_absolute(), "path must be an absolute path"

#     cm = open_write_iff_change(path, "w", force_overwrite=not write_only_if_changed)
#     with cm as f:
#         f.write(contents)

#     return bool(cm.changed)

class FormatUtils:
    @staticmethod
    def extract_sv_width(sv_type:Optional[str]) -> Optional[int]:
        # Expect forms like "logic [31:0]" or "wire [7:0]"
        if not sv_type:
            return None
        m = re.search(r"\[(\d+)\s*:\s*0\]", sv_type)
        return int(m.group(1)) + 1 if m else None

    @staticmethod
    def sv_numeric_literal(value:int, sv_type: Optional[str] = None, makefile_type: Optional[str] = None) -> str:
        w = FormatUtils.extract_sv_width(sv_type)
        if w is not None:
            hexdigs = (w + 3) // 4
            return "{w}'h{v:0{d}X}".format(w=w, v=value, d=hexdigs)
        # Fallback 1:  use makefile_type as hint for hex width
        if makefile_type is not None:
            if makefile_type == "hex":
                return "32'h{0:08X}".format(value)
            elif makefile_type == "hex32":
                return "32'h{0:08X}".format(value)
            elif makefile_type == "hex16":
                return "16'h{0:04X}".format(value)
            elif makefile_type == "hex8":
                return "8'h{0:02X}".format(value)
            elif makefile_type == "decimal":
                return str(value)
            elif makefile_type == "string":
                return str(value)
        # Fallback 2: infer from value's magnitude
        if value < 0:
            return "32'h{0:08X}".format(value)
        elif value > 1<<8:
            return "8'h{0:02X}".format(value)
        elif value > 1<<16:
            return "16'h{0:04X}".format(value)
        # Fallback 3: default to 32-bit hex literal
        return "32'h{0:08X}".format(value)

    @staticmethod
    def format_make_value(v:Any, makefile_type: Optional[str] = None) -> str:
        if isinstance(v, int):
            if makefile_type == "hex":
                return "0x{0:X}".format(v)
            elif makefile_type == "hex32":
                return "0x{0:08X}".format(v)
            elif makefile_type == "hex16":
                return "0x{0:04X}".format(v)
            elif makefile_type == "hex8":
                return "0x{0:02X}".format(v)
            else: # decimal or string type
                return str(v)
        elif isinstance(v, str):
            if makefile_type == "hex":
                return "0x{0:X}".format(int(v))
            elif makefile_type == "hex32":
                return "0x{0:08X}".format(int(v))
            elif makefile_type == "hex16":
                return "0x{0:04X}".format(int(v))
            elif makefile_type == "hex8":
                return "0x{0:02X}".format(int(v))
            elif makefile_type == "decimal":
                return str(int(v))
            else:
                return v
        return str(v)
        
class FileEmitter:
    def __init__(self, config_values:CfgValues, outdir_path:str | Path, emit_files: ConfigFileTypes, verbosity: int = 0):
        self.config_values = config_values
        self.outdir_path = outdir_path
        self.emit_files = emit_files
        self.verbosity = verbosity
        self.output_paths = {"makefile": os.path.join(str(self.outdir_path), DEFAULT_OUTFILE_NAMES["makefile"]),
                            "env": os.path.join(str(self.outdir_path), DEFAULT_OUTFILE_NAMES["env"]),
                            "svpkg": os.path.join(str(self.outdir_path), DEFAULT_OUTFILE_NAMES["svpkg"]),
                            "svh": os.path.join(str(self.outdir_path), DEFAULT_OUTFILE_NAMES["svh"]),
                            }
        self.emitter_functions = {  "makefile": self._emit_makefile,
                                    "env": self._emit_env_file,
                                    "svpkg": self._emit_sv_pkg,
                                    "svh": self._emit_svh_defines,
                                    }

    def emit(self, write_only_if_changed: bool = True) -> tuple[list[str], list[str]]:        
        # make list of files we want to emit
        files_to_emit = []
        if self.emit_files & ConfigFileTypes.MAKEFILE:
            files_to_emit.append("makefile")
        if self.emit_files & ConfigFileTypes.ENV:
            files_to_emit.append("env")
        if self.emit_files & ConfigFileTypes.SVPKG:
            files_to_emit.append("svpkg")
        if self.emit_files & ConfigFileTypes.SVH:
            files_to_emit.append("svh")

        files_emitted: list[str] = []    
        files_unchanged: list[str] = []        
        for key in files_to_emit:
            was_overwritten = self.emitter_functions[key](write_only_if_changed)
            if was_overwritten:
                if self.verbosity >= 2:
                    print(f"⭐️ Updated or created: {self.output_paths[key]}")
                files_emitted.append(self.output_paths[key])
            else:
                if self.verbosity >= 2:
                    print(f"(no changes to {self.output_paths[key]})")
                files_unchanged.append(self.output_paths[key])
        return files_emitted, files_unchanged

    def _emit_makefile(self, write_only_if_changed: bool = True) -> bool:
        """
        Emits a Makefile with the config values into <output_path>.

        - If the Makefile does not exist, it is created.
        - If the Makefile already exists, it is only overwritten if the contents are different.

        Returns:
        True if the Makefile was overwritten, False if it was not.
        """
        output_path = self.output_paths["makefile"]
        
        # Generate include guard name from filename
        # e.g., "curv.mk" -> "__CURV_MK__"
        filename = Path(output_path).name
        guard_name = f"__{filename.replace('.', '_').upper()}__"
        
        cm = open_write_iff_change(output_path, "w", force_overwrite=not write_only_if_changed)
        with cm as f:
            # Write include guard header
            f.write(f"ifndef {guard_name}\n")
            f.write(f"{guard_name} := 1\n")
            f.write("\n")
            
            f.write("# Autogenerated by curvcfg. Do not edit.\n")
            for k in sorted(self.config_values.keys()):
                v_obj: CfgValue = self.config_values[k]
                locs = v_obj.meta.locations
                if "all" in locs or "makefiles" in locs:
                    raw = v_obj.get_raw_value()
                    f.write("{k} := {v}\n".format(k=k, v=FormatUtils.format_make_value(raw, v_obj.meta.makefile_type)))
            
            # Write include guard footer
            f.write("\n")
            f.write(f"endif # {guard_name}\n")

        return bool(cm.changed)

    def _emit_env_file(self, write_only_if_changed: bool = True) -> bool:
        """
        Emits a shell environment file with the config values into <output_path>.

        - If the shell environment file does not exist, it is created.
        - If the shell environment file already exists, it is only overwritten if the contents are different.

        Returns:
        True if the shell environment file was overwritten, False if it was not.
        """
        output_path = self.output_paths["env"]
        cm = open_write_iff_change(output_path, "w", force_overwrite=not write_only_if_changed)
        with cm as f:
            f.write("# -----------------------------------------------------------------------------\n")
            f.write("# Autogenerated by curvcfg. Do not edit.\n")
            f.write("# -----------------------------------------------------------------------------\n\n")
            for k in sorted(self.config_values.keys()):
                v_obj: CfgValue = self.config_values[k]
                locs = v_obj.meta.locations
                if "all" in locs or "env" in locs:
                    raw = v_obj.get_raw_value()
                    f.write("{k}={v}\n".format(k=k, v=FormatUtils.format_make_value(raw, v_obj.meta.makefile_type)))

        return bool(cm.changed)

    def _emit_svh_defines(self, write_only_if_changed: bool = True) -> bool:
        """
        Emits a SystemVerilog include header file with the config values into <output_path>.

        - If the SystemVerilog include header file does not exist, it is created.
        - If the SystemVerilog include header file already exists, it is only overwritten if the contents are different.

        Returns:
        True if the SystemVerilog include header file was overwritten, False if it was not.
        """
        output_path = self.output_paths["svh"]
        # Generate guard from filename: e.g., "curvcfg.svh" -> "__CURVCFG_SVH__"
        filename = output_path.name.upper().replace('.', '_')
        guard = f"__{filename}__"
        cm = open_write_iff_change(output_path, "w", force_overwrite=not write_only_if_changed)
        with cm as f:
            f.write("// -----------------------------------------------------------------------------\n")
            f.write("// Autogenerated by curvcfg. Do not edit.\n")
            f.write("// -----------------------------------------------------------------------------\n\n")
            f.write("`ifndef {g}\n`define {g}\n\n".format(g=guard))
            any_defs = False
            longest_key_len = max(len(k) for k in self.config_values.keys())
            for k in sorted(self.config_values.keys()):
                v_obj: CfgValue = self.config_values[k]
                locs = v_obj.meta.locations
                if "all" in locs or "defines" in locs:
                    any_defs = True
                    sv_type = v_obj.meta.sv_type
                    makefile_type = v_obj.meta.makefile_type
                    vtype   = v_obj.meta.type
                    v       = v_obj.get_raw_value()
                    if (vtype  == "int") or (vtype == "enum" and isinstance(v, int)):
                        if (sv_type == "int"):
                            lit = v
                        else:
                            lit = FormatUtils.sv_numeric_literal(v, sv_type, makefile_type)
                        f.write("`define {k} {lit}\n".format(k=k.ljust(longest_key_len+4), lit=lit))
                    elif (vtype == "string") or (vtype == "enum" and isinstance(v, str)):
                        f.write("`define {k} `\"{v}`\"\n".format(k=k.ljust(longest_key_len+4), v=v))
                    elif isinstance(v, int):
                        f.write("`define {k} 32'h{v:08X}\n".format(k=k.ljust(longest_key_len+4), v=v))
                    else:
                        # Strings can be awkward in macro context; still emit something useful.
                        f.write("// {k_comment} = \"{v}\"\n`define {k} `\"{v}`\"\n".format(k_comment=k,k=k.ljust(longest_key_len+4), v=v))
            if not any_defs:
                f.write("// (No defines selected by schema locations)\n")
            f.write("\n`endif // {g}\n".format(g=guard))

        return bool(cm.changed)

    def _emit_sv_pkg(self, write_only_if_changed: bool = True) -> bool:
        """
        Emits a SystemVerilog package file with the config values into <output_path>.

        - If the SystemVerilog package file does not exist, it is created.
        - If the SystemVerilog package file already exists, it is only overwritten if the contents are different.

        Returns:
        True if the SystemVerilog package file was overwritten, False if it was not.
        """
        output_path = self.output_paths["svpkg"]
        pkg_name = output_path.stem.lower()
        cm = open_write_iff_change(output_path, "w", force_overwrite=not write_only_if_changed)
        with cm as f:
            f.write("// -----------------------------------------------------------------------------\n")
            f.write("// Autogenerated by curvcfg. Do not edit.\n")
            f.write("// -----------------------------------------------------------------------------\n\n")
            f.write(f"package {pkg_name};\n\n")
            f.write("  // verilator lint_off UNUSEDPARAM\n")
            for k in sorted(self.config_values.keys()):
                v_obj: CfgValue = self.config_values[k]
                locs = v_obj.meta.locations
                if "all" in locs or "cfgpkg" in locs:
                    sv_type = v_obj.meta.sv_type
                    makefile_type = v_obj.meta.makefile_type
                    vtype   = v_obj.meta.type
                    v       = v_obj.get_raw_value()
                    if (vtype  == "int") or (vtype == "enum" and isinstance(v, int)):
                        if (sv_type == "int"):
                            lit = v
                        else:
                            lit = FormatUtils.sv_numeric_literal(v, sv_type, makefile_type)
                        f.write("  localparam {t} {k} = {lit};\n".format(t=sv_type, k=k, lit=lit))
                    elif (vtype == "string") or (vtype == "enum" and isinstance(v, str)):
                        f.write("  localparam string {k} = \"{v}\";\n".format(k=k, v=v))
                    else:
                        # Fallback types
                        if isinstance(v, int):
                            f.write("  localparam int {k} = {v};\n".format(k=k, v=v))
                        else:
                            f.write("  localparam string {k} = \"{v}\";\n".format(k=k, v=v))
            f.write("  // verilator lint_on UNUSEDPARAM\n\n")
            f.write(f"endpackage : {pkg_name}\n")

        return bool(cm.changed)

    # def _emit_json(self, write_only_if_changed: bool = True) -> bool:
    #     """
    #     Emits a JSON file with the config values into <output_path>.

    #     - If the JSON file does not exist, it is created.
    #     - If the JSON file already exists, it is only overwritten if the contents are different.

    #     Returns:
    #     True if the JSON file was overwritten, False if it was not.
    #     """
    #     output_path = self.output_paths["json"]
    #     flat:Dict[str, str | int | None] = {}
    #     for k in sorted(self.config_values.keys()):
    #         v_obj: CfgValue = self.config_values[k]
    #         locs = v_obj.meta.locations
    #         if "all" in locs or "json" in locs:
    #             flat[k] = v_obj.get_raw_value()

    #     cm = open_write_iff_change(output_path, "w", force_overwrite=not write_only_if_changed)
    #     with cm as f:
    #         json.dump(flat, f, indent=2, sort_keys=True)

    #     return bool(cm.changed)

    # def _emit_config_mk_deps(self, write_only_if_changed: bool = True) -> bool:
    #     """
    #     Emits a Makefile dependencies file that can be included to indicate that each of our
    #     emitted config files depends on the list of toml files that were used to generate them.

    #     - If the Makefile dependencies file does not exist, it is created.
    #     - If the Makefile dependencies file already exists, it is only overwritten if the contents are different.
    #     Unless write_only_if_changed is False, in which case the file is always overwritten.

    #     Returns:
    #     True if the Makefile dependencies file was overwritten, False if it was not.
    #     """
    #     output_path = self.output_paths["config_mk_deps"]
    #     self._ensure_outdir(os.path.dirname(output_path))
    #     temp_output_path = output_path + ".tmp"
    #     deps:list[str] = []
    #     if self.emit_files & ConfigFileTypes.MAKEFILE:
    #         deps.append(self.output_paths["makefile"])
    #     if self.emit_files & ConfigFileTypes.ENV:
    #         deps.append(self.output_paths["env"])
    #     if self.emit_files & ConfigFileTypes.SVPKG:
    #         deps.append(self.output_paths["svpkg"])
    #     if self.emit_files & ConfigFileTypes.SVH:
    #         deps.append(self.output_paths["svh"])
    #     if self.emit_files & ConfigFileTypes.JSON:
    #         deps.append(self.output_paths["json"])
    #     if self.emit_files & ConfigFileTypes.CONFIG_MK_DEPS:
    #         deps.append(self.output_paths["config_mk_deps"])

    #     target_list_str = ' '.join(deps)
    #     toml_list_str = ' '.join(self.tomls_abs_paths)

    #     with open(temp_output_path, "w") as f:
    #         f.write(f"{target_list_str}: {toml_list_str}\n")

    #     # Check if the file changed
    #     file_changed = self._is_file_changed(temp_output_path, output_path)
        
    #     # If the file changed or we are not writing only if changed, overwrite the output file
    #     if (not write_only_if_changed) or file_changed:
    #         os.rename(temp_output_path, output_path)
    #         return True
    #     else:
    #         os.remove(temp_output_path)
    #         return False
