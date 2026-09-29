"""PHY-PUSCH counter contract: modulo increment, clear before enable."""

def step(count, enable, clear, width, increment, has_clear, has_wrap):
    count = 0 if has_clear and clear else ((count+increment) % (1 << width) if enable else count)
    wrap = int(has_clear and clear) if has_wrap else None
    return count, wrap
