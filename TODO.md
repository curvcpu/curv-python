0.  Manually test a `cfgvars generate` command and a `board generate` command with templates.

1.   Remove:

- file_emitter.py
- base_schema_parser.py
- cfgvalue.py

```
1. cfgvalue.py — in use
Exports: CfgValue, CfgValues, MissingVars

Used by:
base_schema_parser.py (imports all three)
curvpaths.py (imports CfgValue, CfgValues)
draw_tables.py (imports CfgValues)
file_emitter.py (imports CfgValue, CfgValues)
curvpath.py (uses CfgValues)

2. base_schema_parser.py — in use
Exports: get_config_values, emit_config_files
get_config_values is called from:
show.py (line 26)
curvpaths.py (lines 35, 124)
emit_config_files is exported but not called externally (only defined)

3. file_emitter.py — in use
Exports: FileEmitter, ConfigFileTypes, ConfigFileTypesForWriting, DEFAULT_OUTFILE_NAMES

Used by:
base_schema_parser.py (line 303: FileEmitter(...), and imports the types)

All exports are used within base_schema_parser.py
```

2.  Delete all e2e tests and start over from scratch with new schema.

