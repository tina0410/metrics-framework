"""Generate CMul RTL and run a cycle-accurate Icarus testbench."""
from basic_support import check_datapath
from modules.CMul import ModuleCMul


def run(params, vectors, tmp_path):
    check_datapath(ModuleCMul, params,
                   {'i_data_1': 2*params['QU_IN_1'].DWT,
                    'i_data_2': 2*params['QU_IN_2'].DWT},
                   2*params['QU_OUT'].DWT, vectors, tmp_path)
