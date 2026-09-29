import itertools
import pytest
from modules.PyTU import QuType, QuMode, OfMode
from BehavModel_CNorm import expected
from tb_CNorm import run


@pytest.mark.parametrize('rounding,overflow', itertools.product(
    list(QuMode.TRN)+list(QuMode.RND), list(OfMode.WRP)+list(OfMode.SAT)))
@pytest.mark.parametrize('signed,qo,latency,reset', [
    (True, QuType(3,0,True), 0, False),
    (False, QuType(6,2,False), 1, True),
    (True, QuType(6,2,False), 3, False),
    (True, QuType(2,-2,False), 2, True),
])
def test_cnorm(tmp_path, signed, qo, latency, reset, rounding, overflow):
    qi = QuType(4,2,signed)
    params = dict(QU_IN=qi,QU_OUT=qo,N_CLK=latency,IF_RST_N=reset,
                  QU_MODE=rounding,OF_MODE=overflow)
    vectors = [({'i_data':bits},expected(bits,qi,qo,rounding,overflow))
               for bits in range(1 << (2*qi.DWT))]
    run(params, vectors, tmp_path)
