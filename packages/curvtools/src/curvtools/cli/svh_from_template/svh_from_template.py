#!/usr/bin/env python3

################################################################################
#
# This script generates a file from a template file.
#
# Example usage:
#
#   curv-svh-from-template --template-file flashdefines.svh.tmpl \
#                          --output-file flashdefines.svh        \
#                          --var BASE_DIR=/path/to/base/dir
#
################################################################################

import argparse
import os
import sys

def gen_from_template(vars, template_file, output_file):
    with open(template_file, 'r') as f:
        template = f.read()
    
    content = template
    # Replace placeholders with provided variables
    for key, value in vars.items():
        content = content.replace(f'{{{key}}}', value)
    
    # Write the content to the file
    if (output_file=="-"):
        print(content)
    else:
        with open(output_file, 'w') as f:
            f.write(content)
        print(f"Generated {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Transform a template file into an output file with variable substitution')
    parser.add_argument('--template-file', '-t', required=False, help='Template file to transform (default: [OUTPUT_FILE].tmpl)')
    parser.add_argument('--output-file', '-o', required=True, help='Output file to write')
    parser.add_argument('--var', '-v', required=True, action='append', help='Variable to substitute (e.g. DIR=path/to/dir); can be specified multiple times')
    args = parser.parse_args()
    
    vars = {}
    for var in args.var:
        key, value = var.split('=')
        vars[key] = value

    template_file = args.template_file
    if template_file is None:
        template_file = args.output_file + '.tmpl'
        if not os.path.exists(template_file):
            raise FileNotFoundError(f"error:template file {template_file} not found; specify one with --template-file/-t")

    gen_from_template(vars, template_file, args.output_file)

if __name__ == '__main__':
    try:
        main() 
    except Exception as e:
        print(f"aborted: {e}")
        sys.exit(1)