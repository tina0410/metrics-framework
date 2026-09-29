from basic_support import check_datapath
from modules.CNorm import ModuleCNorm


def run(params, vectors, tmp_path):
    check_datapath(ModuleCNorm, params, {'i_data': 2*params['QU_IN'].DWT},
                   params['QU_OUT'].DWT, vectors, tmp_path)
