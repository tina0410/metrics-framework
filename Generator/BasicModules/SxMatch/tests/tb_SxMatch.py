from basic_support import check_datapath
from modules.SxMatch import ModuleSxMatch


def run(params, vectors, tmp_path):
    check_datapath(ModuleSxMatch, params, {'i_data':params['QU_IN'].DWT},
                   params['QU_OUT'].DWT, vectors, tmp_path)
