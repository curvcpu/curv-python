# Memory Map


Auto-generated from memory_map.toml

```text
                                            Size    Access      Cacheable  
                                            ----    ------      ---------  
                 +---------------------+                                   
    0600_10ff    |                     |                                   
                 |                     |                                   
                 |    Flash Control    |    4kb        -            -      
                 |                     |                                   
    0600_0000    |                     |                                   
                 +---------------------+                                   
    0500_0073    |                     |                                   
                 |                     |                                   
                 |     Peripherals     |    116b       -            -      
                 |                     |                                   
    0500_0000    |                     |                                   
                 +---------------------+                                   
    0341_dfff    |                     |                                   
                 |                     |                                   
                 |        BRAM         |    4mb      R/W           Yes     
                 |                     |                                   
    0300_0000    |                     |                                   
                 +---------------------+                                   
    02ff_ffff    |                     |                                   
                 |                     |                                   
                 |      Flash ROM      |    16mb     R/O           Yes     
                 |                     |                                   
    0200_0000    |                     |                                   
                 +---------------------+                                   
    01ff_ffff    |                     |                                   
                 |                     |                                   
                 |        SDRAM        |    32mb     R/W           Yes     
                 |                     |                                   
    0000_0000    |                     |                                   
                 +---------------------+                                   

```

## Flash Registers

| Address | Register | Access | Size |
|---------|----------|--------|------|
| 06000000 - 06000003 | cmd_reg | W/O | 4 |
| 06000004 - 06000007 | cmd_addr | R/W | 4 |
| 06000008 - 0600000b | tag_hi | R/W | 4 |
| 0600000c - 0600000f | tag_lo | R/W | 4 |
| 06000010 - 06000013 | status | R/O | 4 |

## Peripherals Registers

| Address | Register | Access | Size |
|---------|----------|--------|------|
| 05000000 - 05000003 | uart.rx_status | R/O | 4 |
| 05000004 - 05000007 | uart.tx_status | R/O | 4 |
| 05000008 - 0500000b | uart.rx_read_addr | R/O | 4 |
| 0500000c - 0500000f | uart.tx_write_addr | W/O | 4 |
| 05000010 - 05000013 | spi.rx_status | R/O | 4 |
| 05000014 - 05000017 | spi.tx_status | R/O | 4 |
| 05000018 - 0500001b | spi.rx_read_addr | R/O | 4 |
| 0500001c - 0500001f | spi.tx_write_addr | W/O | 4 |
| 05000020 - 05000023 | i2c.rx_status | R/O | 4 |
| 05000024 - 05000027 | i2c.tx_status | R/O | 4 |
| 05000028 - 0500002b | i2c.rx_read_addr | R/O | 4 |
| 0500002c - 0500002f | i2c.tx_write_addr | W/O | 4 |
| 05000040 - 05000043 | gpio.dir | R/W | 4 |
| 05000044 - 05000047 | gpio.inputs | R/O | 4 |
| 0500004c - 0500004f | gpio.outputs | W/O | 4 |
| 05000060 - 05000063 | leds.outputs | W/O | 4 |
| 05000070 - 05000073 | switches.inputs | R/O | 4 |

## Flash Buffers

| Address | Buffer | Access | Size |
|---------|--------|--------|------|
| 06001000 - 060010ff | page_buffer | R/W | 256 |

## BRAM Buffers

| Address | Buffer | Access | Size |
|---------|--------|--------|------|
| 03000000 - 03005fff | oled1 | R/W | 24kb |
| 03006000 - 0300bfff | oled2 | R/W | 24kb |
| 0300c000 - 03011fff | oled3 | R/W | 24kb |
| 03012000 - 03017fff | oled4 | R/W | 24kb |
| 03018000 - 0301dfff | oled5 | R/W | 24kb |
| 0301e000 - 0341dfff | vga | R/W | 4mb |
