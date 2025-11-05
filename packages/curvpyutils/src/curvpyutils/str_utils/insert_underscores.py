def insert_underscores(numeric_str: str, N=4, start_left=False) -> str:
    """
    Insert underscores every N digits from the right
    Args:
        numeric_str: the number's string representation to insert underscores into, e.g. '0x12345678'
        N: The number of digits to insert an underscore between, e.g. 4
        start_left: whether to start inserting underscores from the left (default is False (insert from the right))
    Returns:
        The number's string representation with underscores inserted, e.g.: '0x1234_5678'
    Notes:
        If the number's string representation starts with `0x`, `0b`, or a verilog prefix like `32'h`, we'll strip
        that prefix, insert the underscores, and then add the prefix back.
    """

    # find the prefix, if any, and temporarily remote it
    prefix = ""
    if numeric_str.startswith("0x"):
        prefix = "0x"
    elif numeric_str.startswith("0b"):
        prefix = "0b"
    else:
        # Match Verilog numeric literal prefixes: [0-9]+'[hdb]
        import re
        verilog_match = re.match(r"(\d+'[hdb])", numeric_str)
        if verilog_match:
            prefix = verilog_match.group(1)
    numeric_str = numeric_str[len(prefix):]

    # if the number already contains underscores, remove them first
    numeric_str = numeric_str.replace("_", "")

    # insert the underscores according to the args
    parts = []
    if start_left:
        for i in range(0, len(numeric_str), N):
            parts.append(numeric_str[i:i+N])
    else:
        for i in range(len(numeric_str)-N, -N, -N):
            if i < 0:
                parts.insert(0, numeric_str[0:i+N])
            else:
                parts.insert(0, numeric_str[i:i+N])
    
    # return the prefix and the parts joined by underscores
    return prefix + '_'.join(filter(None, parts))
