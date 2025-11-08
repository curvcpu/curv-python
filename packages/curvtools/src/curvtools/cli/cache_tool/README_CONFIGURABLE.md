# Configurable Cache Tool (cache_tool4)

The cache_tool4 program has been enhanced to support configurable cache parameters while maintaining backward compatibility with the original hardcoded implementation.

## Features

### Configurable Parameters
- **Number of sets**: 4 to 128 (must be power of 2)
- **Number of ways**: 2 (currently only 2-way associative is supported)
- **Address width**: 10 to 32 bits
- **Words per cache line**: 16 (currently only 16 32-bit words per cache line is supported)
- **Tags have valid and dirty bits**: Whether tags have two low bits appended: {valid, dirty}
- **Write hex files with addresses**: Whether to write hex files with @-addresses
- **Base address**: Base address for I$ start (decimal or 0x...)
- **Subdirectories**: Subdirectories for icache, dcache, cachelines, tagram

### Address Layout
The tool automatically calculates the optimal bit layout based on configuration:
- **Offset**: [5:2] (4 bits for 16 words) - always fixed
- **Index**: Variable width based on number of sets
- **Tag**: Remaining high-order bits up to address width
- **Unused**: [1:0] (2 bits for word alignment) - always fixed

## Usage

### Basic Usage
```bash
curv-cache-tool input.hex -o output_dir [options]
```

### Environment Defaults (-e / --config-env-file)
You can provide defaults via a .env file using `-e` (or `--config-env-file`). Keys correspond to the CLI defaults (e.g., `CFG_CACHE_SETS`, `CFG_CACHE_HEX_FILES_SUBDIRS_ICACHE`, etc.).

Example:
```bash
curv-cache-tool \
  packages/curvtools/test/curvtools/cache_tool/test_vectors/cache_tool4/input/icache_dcache_combined.hex \
  -o out \
  -e packages/curvtools/test/curvtools/cache_tool/test_vectors/cache_tool4/input/curv-config.env \
  --no-hex-file-addresses --icache-only

curv-cache-tool \
  packages/curvtools/test/curvtools/cache_tool/test_vectors/cache_tool4/input/icache_dcache_combined.hex \
  -o out \
  -e packages/curvtools/test/curvtools/cache_tool/test_vectors/cache_tool4/input/curv-config.env \
  --no-hex-file-addresses --dcache-only
```

### Examples

#### 4-set cache with 10-bit addresses
```bash
curv-cache-tool input.hex -o output_dir --num-sets 4 --address-width 10
```

## Output Files

The tool generates cache initialization files with names based on configuration:
- `icache/cachelines/way{0,1}.hex`: Instruction cache line RAM
- `icache/tagram/way{0,1}.hex`: Instruction cache tag RAM
- `dcache/cachelines/way{0,1}.hex`: Data cache line RAM  
- `dcache/tagram/way{0,1}.hex`: Data cache tag RAM

## Memory Requirements

The input hex file must contain enough data for both instruction and data caches:
- **4 sets, 16 words per cache line**: 256 words (1024 bytes) total
- **8 sets, 16 words per cache line**: 512 words (2048 bytes) total

## Interleaver CLI

Use the companion CLI to interleave tag RAM ways:
```bash
curv-tag-ram-way-interleaver WAY0_BINARY_FILE WAY1_BINARY_FILE -o interleaved.bin
```

## Running Tests

Two unittest suites are provided under `test/`:

- **cache_tool4 suite**: generates outputs from the combined input hex using the env defaults and compares against `test/test_vectors/cache_tool4/expected/` (including `cache_readme.txt`).
- **interleaver suite**: runs `tag_ram_way_interleaver.py` on provided `way0.hex`/`way1.hex` inputs and compares the resulting `interleaved.bin` against `test/test_vectors/interleaver/expected/`.

Run unit tests from the repo root:
```bash
make test-unit
```

Prerequisites:
- The `delta` binary must be in your PATH for readable diffs.