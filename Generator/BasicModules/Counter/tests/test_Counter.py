import itertools
import pytest
from tb_Counter import run
from basic_support import generate
from modules.Counter import ModuleCounter


@pytest.mark.parametrize('reset,clear,wrap', itertools.product([False,True],repeat=3))
@pytest.mark.parametrize('width,increment', [(1,1),(3,1),(4,3),(3,11)])
def test_counter(tmp_path, reset, clear, wrap, width, increment):
    run(dict(DWT=width,STEP=increment,IF_RST_N=reset,HAS_CLEAR=clear,HAS_WRAP=wrap),tmp_path)


@pytest.mark.parametrize('key,value,error', [('DWT',0,ValueError),('STEP',0,ValueError),
                                           ('DWT',1.5,TypeError),('STEP',True,TypeError)])
def test_invalid_counter(tmp_path,key,value,error):
    params = dict(DWT=4,STEP=1,IF_RST_N=True,HAS_CLEAR=True,HAS_WRAP=True)
    params[key] = value
    with pytest.raises(error):
        generate(ModuleCounter,params,tmp_path)
