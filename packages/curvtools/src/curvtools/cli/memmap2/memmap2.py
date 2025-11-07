#!/usr/bin/env python3
"""
Memory map tool v2 - simplified TOML-based memory map generator
"""
import argparse
import sys
from pathlib import Path
import os

DEFAULT_USE_INSIDE_RANGE_CONDITION = True

def make_dirs(file_path):
    """Create parent directories for file_path, similar to `mkdir -p`"""
    parent_dir = os.path.dirname(file_path)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Memory Map Tool v2 - Generate SystemVerilog and/or documentation from TOML config',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --validate-only memory_map.toml
  %(prog)s --config memory_map.toml --output - > memmappkg.sv                            # write to stdout
  %(prog)s --config memory_map.toml --generate-docs MEMORY_MAP.md                        # write to file
  %(prog)s --config memory_map.toml --output memmappkg.sv --generate-docs MEMORY_MAP.md  # write to files
  %(prog)s --config memory_map.toml --generate-static-asserts slang_top.sv               # write to file
        """
    )

    parser.add_argument('--config', '-c', default='memory_map.toml', help='TOML configuration file (default: memory_map.toml)')

    # Output file options - at least one required
    parser.add_argument('--output', '-o', help="Output SystemVerilog file (use '-' for stdout)")
    parser.add_argument('--generate-docs', '-d', help='Generate MEMORY_MAP.md documentation file (default: none)')
    parser.add_argument('--validate-only', '-V', action='store_true', help='Only validate the TOML file, do not generate output (default: false)')
    parser.add_argument('--generate-static-asserts', '-G', help='Generate a SystemVerilog file with static asserts for unit tests and linting (slang_top.sv)')
    
    parser.add_argument('--skip-validation', action=argparse.BooleanOptionalAction, default=False, help='Skip TOML validation (use with caution)')
    parser.add_argument('--xlen', type=int, default=32, choices=[32, 64], help='word width (in bits) of the processor that will be using the memory map (default: 32)')
    parser.add_argument('--input_template', '-i', help='Input Jinja2 template file for SystemVerilog generation (default: built-in template)')
    parser.add_argument('--use-inside', action=argparse.BooleanOptionalAction, default=DEFAULT_USE_INSIDE_RANGE_CONDITION, help='Use the inside range condition for the SV file generation (default: true)')

    args = parser.parse_args()

    # Validate that at least one output option is specified (unless validate-only)
    if (
        not args.validate_only and
        not (args.output or args.generate_docs or args.generate_static_asserts)
    ):
        parser.error("At least one of --output, --generate-docs or --generate-static-asserts must be specified")

    return args

def main():
    args = parse_args()

    # Import here to avoid import issues if modules aren't found
    try:
        from .validator import validate_toml_file
        from .sv_generator import generate_sv_from_toml
        from .docs_generator.docs_generator import generate_memory_map_markdown
    except ImportError as e:
        print(f"ERROR: Failed to import required modules: {e}")
        print("Make sure you're running this from the memmap2 directory")
        return 1

    # Handle validate-only mode
    if args.validate_only:
        success, _ = validate_toml_file(args.config, xlen=args.xlen, quiet=False)
        return 0 if success else 1

    # Validate TOML file once for all generation operations
    if not args.skip_validation:
        success, _ = validate_toml_file(args.config, xlen=args.xlen, quiet=True)
        if not success:
            print("Validation failed, aborting generation")
            return 1

    # Generate SV file if requested
    if args.output:
        make_dirs(args.output)
        # Use default template if no input file specified
        template_file = args.input_template
        success = generate_sv_from_toml(
            args.config,
            args.output,
            skip_validation=True,
            xlen=args.xlen,
            template_file=template_file,
            use_inside_range_condition=args.use_inside
        )
        if not success:
            return 1

    # Generate docs if requested
    if args.generate_docs:
        make_dirs(args.generate_docs)
        generate_memory_map_markdown(args.config, args.generate_docs, args.xlen)

    # Generate static asserts if requested
    if args.generate_static_asserts:
        try:
            from .gen_static_asserts.gen_static_asserts import generate_static_asserts_from_toml
            make_dirs(args.generate_static_asserts)
            generate_static_asserts_from_toml(args.config, args.generate_static_asserts, args.xlen)
            print(f"Generated {args.generate_static_asserts}")
        except Exception as e:
            print(f"ERROR: Failed to generate static asserts: {e}")
            return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
