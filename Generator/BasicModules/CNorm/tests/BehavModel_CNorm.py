from basic_support import unpack, convert_int


def expected(bits, qi, qo, rounding, overflow):
    re, im = unpack(bits, qi)
    return convert_int(abs(re)+abs(im), qi.FRAC, qo, rounding, overflow)
