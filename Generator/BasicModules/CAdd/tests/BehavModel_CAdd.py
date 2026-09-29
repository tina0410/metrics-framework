"""Exact integer complex arithmetic; independent of the RTL structure."""
from basic_support import unpack, pack, convert_int


def expected(a, b, q1, q2, qo, rounding, overflow):
    ar, ai = unpack(a, q1)
    br, bi = unpack(b, q2)
    frac = max(q1.FRAC, q2.FRAC)
    re = (ar << (frac-q1.FRAC)) + (br << (frac-q2.FRAC))
    im = (ai << (frac-q1.FRAC)) + (bi << (frac-q2.FRAC))
    return pack(convert_int(re, frac, qo, rounding, overflow),
                convert_int(im, frac, qo, rounding, overflow), qo.DWT)
