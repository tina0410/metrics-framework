import itertools
import random
import pytest
from modules.PyTU import QuType, QuMode, OfMode
from BehavModel_CAdd import expected
from tb_CAdd import run
from basic_support import pack

POLICIES = list(itertools.product(list(QuMode.TRN)+list(QuMode.RND),
                                 list(OfMode.WRP)+list(OfMode.SAT)))
CONFIGS = [
    (QuType(4,2,True), QuType(3,1,True), QuType(5,1,True), 0, False),
    (QuType(4,1,False), QuType(3,2,False), QuType(4,0,False), 1, True),
    (QuType(4,3,True), QuType(3,0,False), QuType(6,2,True), 3, False),
    (QuType(3,-2,False), QuType(4,6,True), QuType(4,-1,False), 2, True),
]


@pytest.mark.parametrize('rounding,overflow', POLICIES)
@pytest.mark.parametrize('q1,q2,qo,latency,reset', CONFIGS)

def test_CAdd(tmp_path, q1, q2, qo, latency, reset, rounding, overflow):
    params = dict(QU_IN_1=q1, QU_IN_2=q2, QU_OUT=qo, N_CLK=latency,
                  IF_RST_N=reset, QU_MODE=rounding, OF_MODE=overflow)
    rng = random.Random(20260924)
    m1, m2 = (1 << q1.DWT)-1, (1 << q2.DWT)-1
    edges1 = [0, 1, m1//2, m1//2+1, m1]
    samples = [(a, b, c, d) for a,b in itertools.product(edges1,repeat=2)
               for c,d in [(0,0),(1,1),(m2//2+1,m2),(m2,m2)]]
    samples += [(rng.randrange(m1+1),rng.randrange(m1+1),
                 rng.randrange(m2+1),rng.randrange(m2+1)) for _ in range(128)]
    vectors = []
    for ar, ai, br, bi in samples:
        a, b = pack(ar,ai,q1.DWT), pack(br,bi,q2.DWT)
        vectors.append(({'i_data_1':a,'i_data_2':b},
                        expected(a,b,q1,q2,qo,rounding,overflow)))
    run(params, vectors, tmp_path)
