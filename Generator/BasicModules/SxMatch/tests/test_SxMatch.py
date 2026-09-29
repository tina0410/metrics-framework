import itertools
import pytest
from modules.PyTU import QuType, QuMode, OfMode
from BehavModel_SxMatch import expected
from tb_SxMatch import run


@pytest.mark.parametrize('rounding,overflow', itertools.product(
    list(QuMode.TRN)+list(QuMode.RND), list(OfMode.WRP)+list(OfMode.SAT)))
@pytest.mark.parametrize('shift', [-12,-3,0,2,12])
@pytest.mark.parametrize('signed_in,signed_out,latency,reset', [
    (True,True,0,False), (False,False,1,True), (True,False,3,False),
])
def test_sxmatch(tmp_path, shift, signed_in, signed_out, latency, reset, rounding, overflow):
    qi, qo = QuType(5,2,signed_in), QuType(4,1,signed_out)
    params = dict(QU_IN=qi,QU_OUT=qo,SHIFT=shift,N_CLK=latency,
                  IF_RST_N=reset,QU_MODE=rounding,OF_MODE=overflow)
    vectors = [({'i_data':bits},expected(bits,qi,qo,shift,rounding,overflow))
               for bits in range(1 << qi.DWT)]
    run(params, vectors, tmp_path)
