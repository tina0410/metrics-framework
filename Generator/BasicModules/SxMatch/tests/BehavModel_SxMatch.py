from basic_support import decode, convert_int


def expected(bits, qi, qo, shift, rounding, overflow):
    return convert_int(decode(bits, qi), qi.FRAC-shift, qo, rounding, overflow)
