# Description: A Pytest Frame
# Author: Yifang Dai
# Date: 2025.7.22

import sys
import os 
import re
# from tests.parameters import Parameters
from os.path import dirname, abspath
# sys.path.append('/home/xjy-ubuntu/docs/AutoGen/VeriTests')
sys.path.append(dirname(dirname(__file__)))
sys.path.append(dirname(__file__))

import random
try:
    import pytest
except ModuleNotFoundError:
    class _PytestMark:
        @staticmethod
        def parametrize(*_args, **_kwargs):
            return lambda function: function

    class _PytestCompat:
        mark = _PytestMark()

        class FixtureRequest:
            pass

    pytest = _PytestCompat()
import os
from pathlib import Path
import subprocess
from tb_PE import *
from BehavModel_PE import *
from PyTU import QuMode, OfMode, QuType
import PyTB
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader  
import numpy as np
import PErela
import Getloop
import GetIS
import copy
import math 
import shutil 
from cpp_validation import validate_generated_cpp_inputs
# Testcase Definition
class Testcase:
    __test__ = False

    DUT_NAME = "PE"    
    '''
    Name of DUT, the naming format is the same as the module folder name.
    '''
    TB_NAME_PREFIX = f"Tb"
    '''
    Prefix of Testbench Name. e.g. **TbAdd**0000000001.v. Should not be modified.
    '''
    CPP_CONFIG_FILE_NAME_PREFIX = f"CppConfig"    
    CPP_RUN_FILE_NAME_PREFIX = "CppRun"
    CPP_CONFIG_FILE_NAME_DEST = "config.h"
    CPP_RUN_FILE_NAME_DEST = f"{DUT_NAME}.cpp"
    ROOT_DIR = '.'
    
    def __init__(self, ConfigFileName:str):
        '''
        You need to declare **all** parameters you want to test in test_xxx function.
        '''
        # Load Configuration
        import json
        
        try:
            with open(ConfigFileName, 'r', encoding='utf-8-sig') as f:
                config = json.load(f)
            
            # Load basic parameters from config
            Tx = config.get("Number of Transmit Antennas", 16)
            Rx = config.get("Number of Receiving Antennas", 256)

            ITERATIONS = config.get("Iterations", 2)
            IF_RST_N = config.get("Interface Reset Active Low", True)
            ADDERTREE_PIPELINES = config.get("Adder Tree Pipelines", 1)
            CLOCK_PERIOD_NS = float(config.get("clock", {}).get("period_ns", 10.0))
            if not math.isfinite(CLOCK_PERIOD_NS) or CLOCK_PERIOD_NS <= 0:
                raise ValueError("clock.period_ns must be a finite value greater than zero")
            SIMULATION_FRAMES = int(config.get("flow", {}).get("simulation_frames", 3))
            if SIMULATION_FRAMES < 2:
                raise ValueError("flow.simulation_frames must be at least 2")
            
            # Load input quantization types
            qu_h_config = config.get("Quantization format of H", {"bitwidth": 9, "fractional width": 8, "signed": True})
            QU_IN_H = QuType(qu_h_config["bitwidth"], qu_h_config["fractional width"], qu_h_config["signed"])
            
            qu_y_config = config.get("Quantization format of y", {"bitwidth": 9, "fractional width": 4, "signed": True})
            QU_IN_y = QuType(qu_y_config["bitwidth"], qu_y_config["fractional width"], qu_y_config["signed"])
            
            qu_a_config = config.get("Quantization format of a", {"bitwidth": 4, "fractional width": 4, "signed": True})
            QU_IN_a = QuType(qu_a_config["bitwidth"], qu_a_config["fractional width"], qu_a_config["signed"])
            
            qu_d_config = config.get("Quantization format of D", {"bitwidth": 5, "fractional width": 4, "signed": True})
            QU_IN_D = QuType(qu_d_config["bitwidth"], qu_d_config["fractional width"], qu_d_config["signed"])
            
            # Load output quantization types
            qu_ymf_config = config.get("Quantization format of ymf", {"bitwidth": 9, "fractional width": 4, "signed": True})
            QU_OUT_ymf = QuType(qu_ymf_config["bitwidth"], qu_ymf_config["fractional width"], qu_ymf_config["signed"])
            
            qu_x1_config = config.get("Quantization format of x1", {"bitwidth": 9, "fractional width": 4, "signed": True})
            QU_OUT_x1 = QuType(qu_x1_config["bitwidth"], qu_x1_config["fractional width"], qu_x1_config["signed"])
            
            qu_b2_config = config.get("Quantization format of b2", {"bitwidth": 9, "fractional width": 4, "signed": True})
            QU_OUT_b2 = QuType(qu_b2_config["bitwidth"], qu_b2_config["fractional width"], qu_b2_config["signed"])
            
            qu_d2_config = config.get("Quantization format of d2", {"bitwidth": 9, "fractional width": 4, "signed": True})
            QU_OUT_d2 = QuType(qu_d2_config["bitwidth"], qu_d2_config["fractional width"], qu_d2_config["signed"])
            
            qu_Dx1_config = config.get("Quantization format of Dx1", {"bitwidth": 9, "fractional width": 4, "signed": True})
            QU_OUT_Dx1 = QuType(qu_Dx1_config["bitwidth"], qu_Dx1_config["fractional width"], qu_Dx1_config["signed"])
            
            qu_x2_config = config.get("Quantization format of x2", {"bitwidth": 9, "fractional width": 4, "signed": True})
            QU_OUT_x2 = QuType(qu_x2_config["bitwidth"], qu_x2_config["fractional width"], qu_x2_config["signed"])
            
            qu_b3_config = config.get("Quantization format of b3", {"bitwidth": 9, "fractional width": 4, "signed": True})
            QU_OUT_b3 = QuType(qu_b3_config["bitwidth"], qu_b3_config["fractional width"], qu_b3_config["signed"])
            
            qu_d3_config = config.get("Quantization format of d3", {"bitwidth": 9, "fractional width": 4, "signed": True})
            QU_OUT_d3 = QuType(qu_d3_config["bitwidth"], qu_d3_config["fractional width"], qu_d3_config["signed"])
            
            qu_Dx2_config = config.get("Quantization format of Dx2", {"bitwidth": 9, "fractional width": 4, "signed": True})
            QU_OUT_Dx2 = QuType(qu_Dx2_config["bitwidth"], qu_Dx2_config["fractional width"], qu_Dx2_config["signed"])
            
            qu_x3_config = config.get("Quantization format of x3", {"bitwidth": 9, "fractional width": 4, "signed": True})
            QU_OUT_x3 = QuType(qu_x3_config["bitwidth"], qu_x3_config["fractional width"], qu_x3_config["signed"])
            
            qu_b4_config = config.get("Quantization format of b4", {"bitwidth": 9, "fractional width": 4, "signed": True})
            QU_OUT_b4 = QuType(qu_b4_config["bitwidth"], qu_b4_config["fractional width"], qu_b4_config["signed"])
            
            qu_d4_config = config.get("Quantization format of d4", {"bitwidth": 9, "fractional width": 4, "signed": True})
            QU_OUT_d4 = QuType(qu_d4_config["bitwidth"], qu_d4_config["fractional width"], qu_d4_config["signed"])
            
            qu_Dx3_config = config.get("Quantization format of Dx3", {"bitwidth": 9, "fractional width": 4, "signed": True})
            QU_OUT_Dx3 = QuType(qu_Dx3_config["bitwidth"], qu_Dx3_config["fractional width"], qu_Dx3_config["signed"])
            
            qu_x4_config = config.get("Quantization format of x4", {"bitwidth": 9, "fractional width": 4, "signed": True})
            QU_OUT_x4 = QuType(qu_x4_config["bitwidth"], qu_x4_config["fractional width"], qu_x4_config["signed"])
            
            # Load mode configurations
            qu_mode_str = config.get("Quantization Mode", "TRN.TCPL")
            if qu_mode_str == "TRN.TCPL":
                QU_MODE = QuMode.TRN.TCPL
            elif qu_mode_str == "TRN.SMGN":
                QU_MODE = QuMode.TRN.SMGN
            elif qu_mode_str == "RND.POS_INF":
                QU_MODE = QuMode.RND.POS_INF
            elif qu_mode_str == "RND.NEG_INF":
                QU_MODE = QuMode.RND.NEG_INF
            elif qu_mode_str == "RND.ZERO":
                QU_MODE = QuMode.RND.ZERO
            elif qu_mode_str == "RND.INF":
                QU_MODE = QuMode.RND.INF
            elif qu_mode_str == "RND.CONV":
                QU_MODE = QuMode.RND.CONV
            else:
                print(f"Warning: Unknown Quantization Mode '{qu_mode_str}', using default TRN.TCPL")
                QU_MODE = QuMode.TRN.TCPL
            
            of_mode_str = config.get("Overflow Mode", "WRP.TCPL")
            if of_mode_str == "WRP.TCPL":
                OF_MODE = OfMode.WRP.TCPL
            elif of_mode_str == "SAT.TCPL":
                OF_MODE = OfMode.SAT.TCPL
            elif of_mode_str == "SAT.SMGN":
                OF_MODE = OfMode.SAT.SMGN
            elif of_mode_str == "SAT.ZERO":
                OF_MODE = OfMode.SAT.ZERO
            else:
                print(f"Warning: Unknown Overflow Mode '{of_mode_str}', using default WRP.TCPL")
                OF_MODE = OfMode.WRP.TCPL
            
            PIPELINE_STAGES = config.get("Pipeline Stages", {"Multiplication": 1, "Adder Tree": 1})
            
        except FileNotFoundError:
            print(f"Warning: Config file {ConfigFileName} not found. Using default parameters.")
            # Use default parameters
            Tx = 16
            Rx = 256
            ITERATIONS = 2
            IF_RST_N = True
            ADDERTREE_PIPELINES = 3
            CLOCK_PERIOD_NS = 10.0
            SIMULATION_FRAMES = 3
            
            QU_IN_H = QuType(9, 8, True)
            QU_IN_y = QuType(9, 4, True)
            QU_IN_a = QuType(4, 4, True)
            QU_IN_D = QuType(5, 4, True)
            
            QU_OUT_ymf = QuType(9, 4, True)
            QU_OUT_x1 = QuType(9, 4, True)
            QU_OUT_b2 = QuType(9, 4, True)
            QU_OUT_d2 = QuType(9, 4, True)
            QU_OUT_Dx1 = QuType(9, 4, True)
            QU_OUT_x2 = QuType(9, 4, True)
            QU_OUT_b3 = QuType(9, 4, True)
            QU_OUT_d3 = QuType(9, 4, True)
            QU_OUT_Dx2 = QuType(9, 4, True)
            QU_OUT_x3 = QuType(9, 4, True)
            QU_OUT_b4 = QuType(9, 4, True)
            QU_OUT_d4 = QuType(9, 4, True)
            QU_OUT_Dx3 = QuType(9, 4, True)
            QU_OUT_x4 = QuType(9, 4, True)
            
            QU_MODE = QuMode.TRN.TCPL
            OF_MODE = OfMode.WRP.TCPL

        
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in config file {ConfigFileName}: {e}")
            return
        
        except Exception as e:
            print(f"Error loading config: {e}")
            return
        self.QU_IN_1 = QU_IN_H
        self.QU_IN_2 = QU_IN_y
        self.QU_IN_3 = QU_IN_a
        self.QU_IN_4 = QU_IN_D
        self.QU_OUT =  QU_OUT_ymf
        self.QU_OUT_1 =  QU_OUT_ymf
        self.QU_OUT_2 = QU_OUT_x1
        self.QU_OUT_3 = QU_OUT_b2
        self.QU_OUT_4 = QU_OUT_d2
        self.QU_OUT_5 = QU_OUT_Dx1
        self.QU_OUT_6 = QU_OUT_x2
        self.QU_OUT_7 = QU_OUT_b3
        self.QU_OUT_8 = QU_OUT_d3
        self.QU_OUT_9 = QU_OUT_Dx2
        self.QU_OUT_10 = QU_OUT_x3
        self.QU_OUT_11 = QU_OUT_b4
        self.QU_OUT_12 = QU_OUT_d4 
        self.QU_OUT_13 = QU_OUT_Dx3
        self.QU_OUT_14 = QU_OUT_x4
        self.IF_RST_N = IF_RST_N
        self.QU_MODE = QU_MODE
        self.OF_MODE = OF_MODE
        self.iterations = ITERATIONS
        self.AdderTree_PIPELINES=ADDERTREE_PIPELINES
        self.CLOCK_PERIOD_NS=CLOCK_PERIOD_NS
        self.N_FRAMES=SIMULATION_FRAMES
        self.Tx=Tx
        self.Rx=Rx
        self.SeqNum = os.environ.get(
            "MIMO_CASE_ID", Path(ConfigFileName).stem.split("_case")[-1]
        )
    def display_info(self):
        '''
        Write the parameters you want to display in error_info.txt
        In most cases, only `info` requires modification.
        ''' 
        QuMode_dict = {PyTU.QuMode.TRN.TCPL: "TRN::TCPL", PyTU.QuMode.TRN.SMGN: "TRN::SMGN", PyTU.QuMode.RND.POS_INF: "RND::POS_INF", PyTU.QuMode.RND.NEG_INF: "RND::NEG_INF", 
                   PyTU.QuMode.RND.INF: "RND::INF", PyTU.QuMode.RND.ZERO: "RND::ZERO",PyTU.QuMode.RND.CONV: "RND::CONV"}
        OfMode_dict = {PyTU.OfMode.WRP.TCPL: "WRP::TCPL", PyTU.OfMode.SAT.TCPL: "SAT::TCPL", PyTU.OfMode.SAT.ZERO: "SAT::ZERO", PyTU.OfMode.SAT.SMGN: "SAT::SMGN"}
        QuMode_str = QuMode_dict[self.QU_MODE]
        OfMode_str = OfMode_dict[self.OF_MODE]
        signed_str = ["False","True"]
        signed_in_1 = signed_str[self.QU_IN_1.IF_SIGNED]
        signed_out = signed_str[self.QU_OUT.IF_SIGNED]
        info = f"QU_IN_1({self.QU_IN_1.DWT}, {self.QU_IN_1.FRAC}, {signed_in_1})\n" + f"QU_OUT({self.QU_OUT.DWT}, {self.QU_OUT.FRAC}, {signed_out})\n" + f"QU_MODE: {QuMode_str}    OF_MODE: {OfMode_str}\n" + f"IF_RST_N: {self.IF_RST_N}"
        return info
    
            
# # At the beginning of the test, clear the generated files
# 
# 
# #---H:in_1---y:in_2---a:in_3----D:in_4---#
# #---ymf:out_1---x1:out_2---b2:out_3---d2:out_4--Dx1:out_5---x2:out_6---b3:out_7---d3:out_8---Dx2:out_9---x3:out_10---b4:out_11---d4:out_12---Dx3:out_13---x4:out_14
# def generate_testcase_specific_value_case1(Testcase):

#     generator = PyTB.TestcaseGenerator(
#         if_rst_n = [True], 
#         dwt_in_1 = [9], 
#         frac_in_1 = [8],  
#         dwt_in_2 = [9], 
#         frac_in_2 = [4],
#         dwt_in_3 = [5],
#         frac_in_3 = [5],
#         dwt_in_4 = [5],
#         frac_in_4 = [4],
#         dwt_out_1 = [9],
#         frac_out_1 = [4], 
#         dwt_out_2 = [9],
#         frac_out_2 = [4], 
#         dwt_out_3 = [9],
#         frac_out_3 = [4], 
#         dwt_out_4 = [9],
#         frac_out_4 = [4], 
#         dwt_out_5 = [9],
#         frac_out_5 = [4], 
#         dwt_out_6 = [9],
#         frac_out_6 = [4], 
#         dwt_out_7 = [9],
#         frac_out_7 = [4], 
#         dwt_out_8 = [9],
#         frac_out_8 = [4], 
#         dwt_out_9 = [9],
#         frac_out_9 = [4], 
#         dwt_out_10 = [9],
#         frac_out_10 = [4], 
#         dwt_out_11 = [9],
#         frac_out_11 = [4], 
#         dwt_out_12 = [9],
#         frac_out_12 = [4], 
#         dwt_out_13 = [9],
#         frac_out_13 = [4], 
#         dwt_out_14 = [9],
#         frac_out_14 = [4], 
#         if_signed_in_1 = [True],
#         if_signed_out_1 = [True], 
#         qu_mode = [PyTU.QuMode.TRN.TCPL],
#         of_mode = [PyTU.OfMode.WRP.TCPL],  
#         iterations = [3],
#         AdderTree_PIPELINES = [3],
#         Tx = [16],
#         Rx = [64],
#     )
    
#     testcase = generator.generate_testcases(Testcase)
    
#     return testcase



def generate_testcase_spec(Testcase):

    selected_config = os.environ.get("MIMO_CONFIG_PATH")
    if selected_config:
        config_paths = [selected_config]
    else:
        config_file_path = "../configs"
        config_paths = [
            os.path.join(config_file_path, filename)
            for filename in os.listdir(config_file_path)
            if filename.endswith(".json")
        ]
    testcase = [Testcase(ConfigFileName=path) for path in config_paths]
    return testcase
# -------------------------------User Settings------------------------------- #
# Testcase Range
testcase = generate_testcase_spec(Testcase)
@pytest.mark.parametrize("Testcase", testcase)

def test_my_module(request: pytest.FixtureRequest,Testcase:Testcase):
    '''
    A Module Tester decorated by Testing Parameters.
    You should modify contents in User Settings to ensure the availability.
    '''
    # -----------------------------User Settings------------------------------------ #
    tb_name_prefix = Testcase.TB_NAME_PREFIX
    cpp_config_file_name_prefix = Testcase.CPP_CONFIG_FILE_NAME_PREFIX
    cpp_run_file_name_prefix = Testcase.CPP_RUN_FILE_NAME_PREFIX
    cpp_config_file_name_dest = Testcase.CPP_CONFIG_FILE_NAME_DEST
    cpp_run_file_name_dest = Testcase.CPP_RUN_FILE_NAME_DEST
    root_dir = Testcase.ROOT_DIR
    QU_IN_1 = Testcase.QU_IN_1
    QU_IN_2 = Testcase.QU_IN_2
    QU = {}
    QU['HT1'] = Testcase.QU_IN_1
    QU['H1'] = Testcase.QU_IN_1
    QU['HT2'] = Testcase.QU_IN_1
    QU['H2'] = Testcase.QU_IN_1
    QU['HT3'] = Testcase.QU_IN_1
    QU['H3'] = Testcase.QU_IN_1
    QU['HT4'] = Testcase.QU_IN_1
    QU['y'] = Testcase.QU_IN_2
    QU['a'] = Testcase.QU_IN_3
    QU['D1'] = Testcase.QU_IN_4
    QU['D2'] = Testcase.QU_IN_4
    QU['D3'] = Testcase.QU_IN_4
    QU['D4'] = Testcase.QU_IN_4
    QU['D5'] = Testcase.QU_IN_4
    QU['D6'] = Testcase.QU_IN_4
    QU['D7'] = Testcase.QU_IN_4
    # IF_ENABLE = Parameters.IF_ENABLE
    QU_OUT = Testcase.QU_OUT
    QU['ymf'] = Testcase.QU_OUT_1
    QU['x1'] = Testcase.QU_OUT_2
    QU['b2'] = Testcase.QU_OUT_3
    QU['d2'] = Testcase.QU_OUT_4
    QU['Dx1'] = Testcase.QU_OUT_5
    QU['x2'] = Testcase.QU_OUT_6
    QU['b3'] = Testcase.QU_OUT_7
    QU['d3'] = Testcase.QU_OUT_8
    QU['Dx2'] = Testcase.QU_OUT_9
    QU['x3'] = Testcase.QU_OUT_10
    QU['b4'] = Testcase.QU_OUT_11
    QU['d4'] = Testcase.QU_OUT_12
    QU['Dx3'] = Testcase.QU_OUT_13
    QU['x4'] = Testcase.QU_OUT_14
    IF_RST_N = Testcase.IF_RST_N
    QU_MODE= Testcase.QU_MODE
    OF_MODE= Testcase.OF_MODE

    iterations = Testcase.iterations
    
    Tx = Testcase.Tx
    Rx = Testcase.Rx
    AdderTree_PIPELINES=Testcase.AdderTree_PIPELINES
    CLOCK_PERIOD_NS=Testcase.CLOCK_PERIOD_NS
    # ------------------------------------------------------------------------------ #
    # Set isolated working directories for this case.
    os.chdir(root_dir)
    test_num = f"Testcase{Testcase.SeqNum}"
    sim_root = Path(os.environ.get("MIMO_SIM_ROOT", "./sim")).resolve()
    design_rtl_root = Path(
        os.environ.get("MIMO_DESIGN_RTL_ROOT", "../RTL")
    ).resolve()
    o_files_path = str(sim_root / "Output_Files")
    i_files_path = str(sim_root / "Input_Files")
    c_files_path = str(sim_root / "Comparison_Files")
    log_files_path = str(sim_root / "Log_Files")
    cpp_root = sim_root / "CppModules"
    cpp_include_root = cpp_root / "include"
    for path in (o_files_path, i_files_path, c_files_path, log_files_path, str(cpp_include_root)):
        os.makedirs(path, exist_ok=True)

    folder_path = str(sim_root / "RTL" / test_num)
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    os.makedirs(folder_path, exist_ok=True)

    

    # Generate RTL code & Testbench
    
    
    moduleloader.set_language_mode('VERILOG')
    moduleloader.set_root_dir(folder_path)
    moduleloader.disEnableWarning()
    moduleloader.set_naming_mode("SEQUENTIAL")

    verilog_run_flag = True
    error_record = []
    N_FRAMES = Testcase.N_FRAMES
    print(f"Genrating Testing RTL Code...")
    code = []
    T=[]
    transpose=[]
    code.append(f"""
for i in range({Tx}):
    for j in range(1):
        for k in range({Rx}):
            ymf[i, j] += HT1[i,k] * y[k, j]
    """)
    
    code.append(f"""
for i in range({Tx}):
    x1[i] = D1[i]*ymf[i]
    """)
#------------for i=2:k do--------------#
    code.append(f"""
for i in range({Rx}):
    for j in range(1):
        for k in range({Tx}):
            b2[i, j] += H1[i,k] * x1[k, j]
    """)
    
    code.append(f"""
for i in range({Tx}):
    for j in range(1):
        for k in range({Rx}):
            d2[i, j] += HT2[i,k] * b2[k, j]
    """)
    
    code.append(f"""
for i in range({Tx}):
    Dx1[i] = D2[i]*x1[i]
    """)
    
    code.append(f"""
for i in range({Tx}):
    x2[i] = x1[i] + x1[i] - a*Dx1[i] + D3[i]*d2[i]
    """)
#----------i=3--------------#    
    code.append(f"""
for i in range({Rx}):
    for j in range(1):
        for k in range({Tx}):
            b3[i, j] += H2[i,k] * x2[k, j]
    """)
    
    code.append(f"""
for i in range({Tx}):
    for j in range(1):
        for k in range({Rx}):
            d3[i, j] += HT3[i,k] * b3[k, j]
    """)
    
    code.append(f"""
for i in range({Tx}):
    Dx2[i] = D4[i]*x2[i]
    """)
    
    code.append(f"""
for i in range({Tx}):
    x3[i] = x1[i] + x2[i] - a*Dx2[i] + D5[i]*d3[i]
    """)
#----------i=4--------------#    
    code.append(f"""
for i in range({Rx}):
    for j in range(1):
        for k in range({Tx}):
            b4[i, j] += H3[i,k] * x3[k, j]
    """)
    
    code.append(f"""
for i in range({Tx}):
    for j in range(1):
        for k in range({Rx}):
            d4[i, j] += HT4[i,k] * b4[k, j]
    """)
    
    code.append(f"""
for i in range({Tx}):
    Dx3[i] = D6[i]*x3[i]
    """)
    
    code.append(f"""
for i in range({Tx}):
    x4[i] = x1[i] + x3[i] - a*Dx3[i] + D7[i]*d4[i]
    """)
        
    T.append(np.array([
        [0, 1, 0],
        [0, 0, 1],
        [1, 0, 0]
    ]))
    T.append(np.array([
        [0],
        [0],
        [1]
    ]))
    T.append(np.array([
        [0, 1, 0],
        [1, 0, 0],
        [0, 0, 1]
    ]))
    T.append(np.array([
        [0, 1, 0],
        [0, 0, 1],
        [1, 0, 0]
    ]))
    T.append(np.array([
        [0],
        [0],
        [1]
    ]))
    T.append(np.array([
        [0],
        [0],
        [1]
    ]))
    T.append(np.array([
        [0, 1, 0],
        [1, 0, 0],
        [0, 0, 1]
    ]))
    T.append(np.array([
        [0, 1, 0],
        [0, 0, 1],
        [1, 0, 0]
    ]))
    T.append(np.array([
        [0],
        [0],
        [1]
    ]))
    T.append(np.array([
        [0],
        [0],
        [1]
    ]))
    T.append(np.array([
        [0, 1, 0],
        [1, 0, 0],
        [0, 0, 1]
    ]))
    T.append(np.array([
        [0, 1, 0],
        [0, 0, 1],
        [1, 0, 0]
    ]))
    T.append(np.array([
        [0],
        [0],
        [1]
    ]))
    T.append(np.array([
        [0],
        [0],
        [1]
    ]))
    tmax=2+iterations*4
###################################################################################################
    Eqn=[]
    Nn=[]
    Mn=[]
    Pn=[]
    In_An=[]
    start_time_an=[]
    end_time_an=[]
    In_Bn=[]
    start_time_bn=[]
    end_time_bn=[]
    Out_Cn=[]
    In_Cn=[]
    end_time_Cn=[]
    start_time_Cn=[]
    unique_pe_addressesn=[]
    passan=[]
    passbn=[]
    passcn=[]
    dependency_matricesn=[]
    code_linen=[]
    print("aaa",code)
    
    for tn in range(tmax):
        if T[tn].shape == (3,3):
            eqarrays = re.findall(r'(\w+)\s*\[', code[tn])
            Eq=list(dict.fromkeys(eqarrays)) 
            # print("AT", AT)
            # print("BT", BT)
            range_values = []  
            for line in code[tn].splitlines():
                line = line.strip()  
                if 'range(' in line:  
                    start = line.index('range(') + len('range(')
                    end = line.index(')', start)
                    value = int(line[start:end])  
                    range_values.append(value)  
            N, M, P = (range_values + [None, None, None])[:3]

            dependency_matrices = Getloop.get_dependency_matrices(code[tn])
            global_loop_vars = dependency_matrices[next(iter(dependency_matrices))][1]
            print("Global Loop Variables:", global_loop_vars)
            
            solution = np.eye(3)
            i = 0
            for var_name, (matrix, loop_vars) in dependency_matrices.items():
                solution[i] = GetIS.find_unit_solution(matrix)
                i += 1
            
            

            pass_pass = np.matmul(T[tn], solution.T)

            pass_pass = np.array(pass_pass, dtype=np.int8)
            print("pass_pass:", pass_pass)


            iteration_vectors = []

            for i in range(N):
                for j in range(M):
                    for k in range(P):
                        iteration_vectors.append((i, j, k))
            # Generate unique PE addresses
            unique_pe_addresses, time = PErela.generate_pe_addresses_and_times(T[tn], iteration_vectors)
            unique_pe_addresses = sorted(unique_pe_addresses)
            

            passa = pass_pass[:, 1]
            passb = pass_pass[:, 2]
            passc = pass_pass[:, 0]
            
            OUTiteration_vectors = []
            for i in range(N):
                for j in range(M):
                    for k in range(P-1,P):
                        OUTiteration_vectors.append((i, j, k))
            if passa[0] == 0 and passa[1] == 0:
                In_A = unique_pe_addresses
                start_time_a = {pe_address: times['start_time'] for pe_address, times in time.items()}
                end_time_a = start_time_a
            else:
                In_A, time_a = PErela.get_edge_points_with_times(unique_pe_addresses, passa[:2], time)
                
                start_time_a = {pe_address: times['start_time'] for pe_address, times in time_a.items()}
                end_time_a = {pe_address: times['end_time'] for pe_address, times in time_a.items()}
            if passb[0] == 0 and passb[1] == 0:
                In_B = unique_pe_addresses
                start_time_b = {pe_address: times['start_time'] for pe_address, times in time.items()}
                end_time_b = start_time_b
            else:
                In_B, time_b = PErela.get_edge_points_with_times(unique_pe_addresses, passb[:2], time)
                start_time_b = {pe_address: times['start_time'] for pe_address, times in time_b.items()}
                end_time_b = {pe_address: times['end_time'] for pe_address, times in time_b.items()}
            if passc[0] == 0 and passc[1] == 0:
                Out_C = unique_pe_addresses
                end_time_C = {pe_address: times['end_time'] for pe_address, times in time.items()}
                In_C = unique_pe_addresses
                start_time_C = end_time_C 
    
                for key in start_time_C:
                    start_time_C[key] = np.int64(start_time_C[key]+ 1)      
            else:
                OutCu, OutCT= PErela.generate_pe_addresses_and_times(T[tn], OUTiteration_vectors)
                OutCT = sorted(OutCT.items(), key=lambda x: (x[0][0], x[0][1]))   
                Out_C = sorted(OutCu)   
                time_c = {
                    (i, j): {'start_time': times['start_time'], 'end_time': times['end_time']}
                    for (i, j), times in OutCT
                }  
                start_time_C = {pe_address: times['start_time'] for pe_address, times in time_c.items()}
                end_time_C = {pe_address: times['end_time'] for pe_address, times in time_c.items()}
                In_C, in_time_c = PErela.get_edge_points_with_times(unique_pe_addresses, passc[:2], time)
                if passc[2]==0:
                    for key in end_time_C:
                        end_time_C[key] = np.int64(end_time_C[key]+ AdderTree_PIPELINES)       
                    for key in start_time_C:
                        start_time_C[key] = np.int64(start_time_C[key]+ AdderTree_PIPELINES)
                       

            Eqn.append(Eq)
            Nn.append(N)
            Mn.append(M)
            Pn.append(P)
            In_An.append(In_A)
            start_time_an.append(start_time_a)
            end_time_an.append(end_time_a)
            In_Bn.append(In_B)
            start_time_bn.append(start_time_b)
            end_time_bn.append(end_time_b)
            Out_Cn.append(Out_C)
            In_Cn.append(In_C)
            end_time_Cn.append(end_time_C)
            start_time_Cn.append(start_time_C)
            unique_pe_addressesn.append(unique_pe_addresses)
            passan.append(passa)
            passbn.append(passb)
            passcn.append(passc)
            dependency_matricesn.append(dependency_matrices)
            code_linen.append(0)
        else:
            if T[tn].shape == (3,1):
                In_A = [(np.int64(0), np.int64(0))]
                In_B=In_A
                In_C=In_A
                Out_C=In_A
                unique_pe_addresses=In_A
                # start_time_a = {
                #     tuple(map(np.int64, item['PE_address'].flatten())): np.int64(item['time'][0])
                #     for item in pe_addresses
                # }
                start_time_a = {(np.int64(0), np.int64(0)): np.int64(0)}
                end_time_a=copy.deepcopy(start_time_a)
                for key in end_time_a:
                    end_time_a[key] = np.int64(end_time_a[key]+ N-1)
                start_time_b=start_time_a
                end_time_b=end_time_a
                Eq= Getloop.extract_variables_in_order(code[tn])
                start_time_C=copy.deepcopy(start_time_a)
                
                lines = code[tn].strip().split('\n')
                code_line = lines[1].strip()

                add_sub_count = code_line.count('+') + code_line.count('-')
                
                for key in start_time_C:
                    start_time_C[key] = np.int64(start_time_C[key]+ math.ceil(math.log2(add_sub_count+1))+1)
                end_time_C=copy.deepcopy(start_time_C)
                for key in end_time_C:
                    end_time_C[key] = np.int64(end_time_C[key]+ N-1)
                # match = re.search(r'range\((\d+)\)', code[tn])
                # if match:
                #     max_range = int(match.group(1))
                #     N = max_range
                # else:
                #     N = 0  
                # pe_addresses = []
                # spatial_coords = []
                # for i in range(N):
                #     i = np.array(i)
                #     S = T[tn].dot(i)
                #     spatial_coord = S[:-1]
                #     time = S[-1]
                #     spatial_coords.append(spatial_coord)
                #     pe_addresses.append({
                #         'PE_address': spatial_coord,
                #         'time': time
                #     })
                # In_A = [tuple(map(np.int64, item['PE_address'].flatten())) for item in pe_addresses]
                # In_B=In_A
                # In_C=In_A
                # Out_C=In_A
                # unique_pe_addresses=In_A
                # start_time_a = {
                #     tuple(map(np.int64, item['PE_address'].flatten())): np.int64(item['time'][0])
                #     for item in pe_addresses
                # }
                # end_time_a=start_time_a
                # start_time_b=start_time_a
                # end_time_b=start_time_a
                # Eq= Getloop.extract_variables_in_order(code[tn])
                # end_time_C=copy.deepcopy(start_time_a)
                
                # lines = code[tn].strip().split('\n')
                # code_line = lines[1].strip()

                # add_sub_count = code_line.count('+') + code_line.count('-')
                
                # for key in end_time_C:
                #     end_time_C[key] = np.int64(end_time_C[key]+ math.ceil(math.log2(add_sub_count+1))+1) 
                # start_time_C=end_time_C
                

                # print("code",code_line)

                code_linen.append(code_line)
                Eqn.append(Eq)
                Nn.append(N)
                Mn.append(1)
                Pn.append(1)
                In_An.append(In_A)
                start_time_an.append(start_time_a)
                end_time_an.append(end_time_a)
                In_Bn.append(In_B)
                start_time_bn.append(start_time_b)
                end_time_bn.append(end_time_b)
                Out_Cn.append(Out_C)
                In_Cn.append(In_C)
                end_time_Cn.append(end_time_C)
                start_time_Cn.append(start_time_C)
                unique_pe_addressesn.append(unique_pe_addresses)
                passan.append(0)
                passbn.append(0)
                passcn.append(0)
                dependency_matricesn.append(0)
            else:
                lines = code[tn].strip().split('\n')
                code_line = lines[2].strip()
                range_values = []  
                for line in code[tn].splitlines():
                    line = line.strip()  
                    if 'range(' in line:  
                        start = line.index('range(') + len('range(')
                        end = line.index(')', start)
                        value = int(line[start:end])  
                        range_values.append(value)  
                N, M = (range_values + [None, None])[:2]
                Eq= Getloop.extract_variables_in_order(code[tn])
                iteration_vector=PErela.extract_iterations(code[tn])
                unique_pe_addresses, time = PErela.generate_pe_addresses_and_times(T[tn], iteration_vector)
                unique_pe_addresses = sorted(unique_pe_addresses)
                print("unique_pe_addresses:",unique_pe_addresses)
                In_A = unique_pe_addresses
                start_time_a = {pe_address: times['start_time'] for pe_address, times in time.items()}
                end_time_C = {pe_address: times['end_time'] for pe_address, times in time.items()}  
                add_sub_count = code_line.count('+') + code_line.count('-')
                start_time_C=copy.deepcopy(start_time_a)
                for key in end_time_C:
                    end_time_C[key] = np.int64(end_time_C[key]+ math.ceil(math.log2(add_sub_count+1))+1) 
                for key in start_time_C:
                    start_time_C[key] = np.int64(start_time_C[key]+ math.ceil(math.log2(add_sub_count+1))+1)     
                end_time_a=start_time_a
                start_time_b=start_time_a
                end_time_b=start_time_a
                
                In_B=In_A
                In_C=In_A
                Out_C=In_A

                code_linen.append(code_line)
                Eqn.append(Eq)
                Nn.append(N)
                Mn.append(M)
                Pn.append(1)
                In_An.append(In_A)
                start_time_an.append(start_time_a)
                end_time_an.append(end_time_a)
                In_Bn.append(In_B)
                start_time_bn.append(start_time_b)
                end_time_bn.append(end_time_b)
                Out_Cn.append(Out_C)
                In_Cn.append(In_C)
                end_time_Cn.append(end_time_C)
                start_time_Cn.append(start_time_C)
                unique_pe_addressesn.append(unique_pe_addresses)
                passan.append(0)
                passbn.append(0)
                passcn.append(0)
                dependency_matricesn.append(0)
    # -----------------------------User Settings------------------------------------ #
   
    #print("end_time_an:", end_time_an[1]) 
    ModuleTbPE(
        iterations=iterations,
        QU=QU,
        QU_IN_1 = QU_IN_1,
        QU_IN_2 = QU_IN_2,
        QU_OUT = QU_OUT,  
        IF_RST_N = IF_RST_N, 
        QU_MODE=QU_MODE, 
        OF_MODE=OF_MODE, 
        N_FRAMES=N_FRAMES,
        CLOCK_PERIOD_NS=CLOCK_PERIOD_NS,
        In_A=In_An,
        start_time_a=start_time_an, 
        In_B=In_Bn,
        start_time_b=start_time_bn,
        Out_C=Out_Cn,
        In_C=In_Cn,
        end_time_C=end_time_Cn,
        start_time_C=start_time_Cn,
        unique_pe_addresses=unique_pe_addressesn,
        passa=passan,
        passb=passbn,
        passc=passcn,
        I=Nn,
        J=Mn,
        K=Pn,
        Eq=Eqn,
        transpose=transpose,
        code_line=code_linen,
        AdderTree_PIPELINES=AdderTree_PIPELINES
        )
    print('done\n')
    moduleloader.reset()
    # ------------------------------------------------------------------------------- #
    #------------------------------------ USE pre-generated RTL code ------------------------------------#
    # Delete all the generated code except the testbench
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    for file in os.listdir(folder_path):
        if file.endswith('.v') and not file.startswith(tb_name_prefix):
            file_path = os.path.join(folder_path, file)
            os.remove(file_path)
    
    # Copy the pre-generated RTL code to the folder
    rtl_path = str(design_rtl_root / test_num)
    for file in os.listdir(rtl_path):
        if file.endswith('.v'):
            src_file_path = os.path.join(rtl_path, file)
            dest_file_path = os.path.join(folder_path, file)
            if not os.path.exists(dest_file_path):
                shutil.copy2(src_file_path, dest_file_path)
        

    # Generate cpp config and run files
    # CAUTION !!!!!! This may overwrite the existing files in the directory !!!!!!
    print(f"Generating cpp config and run files")
    moduleloader.set_root_dir(str(cpp_include_root))
    moduleloader.set_language_mode('CPP_HEADER')

    # PyTB.delete_file('./sim/CppModules/include',cpp_config_file_name_dest)
    # PyTB.delete_file('./sim/CppModules', cpp_run_file_name_dest)

    
    ModuleCppConfig(QU=QU, QU_MODE=QU_MODE, OF_MODE=OF_MODE, Eq=Eqn, I=Nn,J=Mn,K=Pn)
    moduleloader.set_root_dir(str(cpp_root))
    moduleloader.set_language_mode('CPP')
    ModuleCppRun(iterations=iterations, N_FRAMES=N_FRAMES,In_A=In_An, T=T, start_time_a=start_time_an, end_time_a=end_time_an, In_B=In_Bn, start_time_b=start_time_bn,end_time_b=end_time_bn, Out_C=Out_Cn, start_time_C=start_time_Cn,end_time_C=end_time_Cn, dependency_matrices=dependency_matricesn,Eq=Eqn, code_line=code_linen, transpose=transpose, I=Nn,J=Mn,K=Pn)

    # Get the names of generated cpp files
    cpp_config_file_name_gen = list(moduleloader.getParams(cpp_config_file_name_prefix)[-1].keys())[-1] + '.h'
    cpp_run_file_name_gen = list(moduleloader.getParams(cpp_run_file_name_prefix)[-1].keys())[-1] + '.cpp'
    # raise(ValueError)
    PyTB.move_and_rename_file(str(cpp_include_root), str(cpp_include_root), cpp_config_file_name_gen, cpp_config_file_name_dest)
    PyTB.move_and_rename_file(str(cpp_root), str(cpp_root), cpp_run_file_name_gen, cpp_run_file_name_dest)
    validate_generated_cpp_inputs(cpp_root / cpp_run_file_name_dest)
    
    # Running cpp files to generate input and comparison files
    print(f"{PyTB.BLUE}Running cpp file to generate input and comparison files")
    
    cpp_standard_flag = detect_cpp23_standard_flag()
    cpp_compile_command = f"clang++ lNSA.cpp {cpp_run_file_name_dest} {cpp_standard_flag} -Iinclude -ofxp2.out -larmadillo -lblas -llapack"
    cpp_run_command = "./fxp2.out"
    run_subprocess(cpp_compile_command, cwd_in=str(cpp_root))
    run_subprocess(cpp_run_command, cwd_in=str(cpp_root))

    # Collect all verilog files in ./RTL
    verilog_file_list = str()
    for file in os.listdir(folder_path):
        if file.endswith(".v"):
            verilog_file_list += f"{file} "

    print(f"Running iverilog compiler...")

    # verilog_include_path = os.path.join(root_dir, 'sim/RTL')
    # print(verilog_include_path)

    iverilog_command = f"iverilog -o wave {verilog_file_list}"
    print(iverilog_command)
    run_subprocess(iverilog_command, cwd_in=folder_path)

    print(f"Running vvp...")
    vvp_command = f"vvp -n wave -lxt2"
    
    run_subprocess(vvp_command,cwd_in=folder_path)
    
    # Run Comparison
    
    print(f"Running comparison...")

    # ------------------------------User Settings----------------------------------- #


    compare_file_list = [
        (str(sim_root / "Input_Files" / "PE_i_data_D1.txt"),
         str(sim_root / "Comparison_Files" / "PE_o_data.txt"),
         str(sim_root / "Output_Files" / "PE_o_data.txt")),
        ]
    
    clear_flag = True
    for file0, file1, file2 in compare_file_list:
        file0_tmp = file0
        file1_tmp = file1
        file2_tmp = file2
        def is_empty(file_path):
            return os.path.getsize(file_path) == 0

        if is_empty(file1) or is_empty(file2):
            print(f"错误：{file1} 或 {file2} 是空文件！")
            clear_flag = False
        with open(file0, 'r', encoding='utf-8') as file0, open(file1, 'r', encoding='utf-8') as file1, open(file2, 'r', encoding='utf-8') as file2:
            line_number = 0
            for line1, line2 in zip(file1, file2):
                line_number += 1
                if line1.strip() != line2.strip():
                    dec_num1,msg= PyTB.binary_complement_to_decimal(line1.strip(),is_signed = QU_OUT.IF_SIGNED)
                    dec_num2,msg = PyTB.binary_complement_to_decimal(line2.strip(),is_signed = QU_OUT.IF_SIGNED)
                    clear_flag = False
                    if verilog_run_flag:
                        error_record.append(f" {file1_tmp}:{line1.strip()}(d{dec_num1}), {file2_tmp}:{line2.strip()}(d{dec_num2}) \n")

    if (clear_flag):
        print("Results are consistent. \033[1;32;40mVerification Success!\033[0m")
    else:
        print("Results are not consistent. \033[1;31;40mVerfication Failed!\033[0m")
        err_info = Testcase.display_info()
        print(f"\033[1;31;40mERROR IN TEST CASE \n:\033[0m {err_info}")
        PyTB.Log.write_error_info(Testcase, log_files_path, error_record)

    assert clear_flag == True
    print(f"{PyTB.BLUE}Done!")
    # ------------------------------------------------------------------------------ #

def detect_cpp23_standard_flag():
    """Select the spelling for C++23 understood by the installed clang."""
    probe_source = "int main() { return 0; }\n"
    errors = []
    for standard in ("c++23", "c++2b"):
        result = subprocess.run(
            ["clang++", f"-std={standard}", "-x", "c++", "-fsyntax-only", "-"],
            input=probe_source,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode == 0:
            return f"-std={standard}"
        errors.append(f"-std={standard}: {result.stderr.strip()}")
    raise RuntimeError(
        "Installed clang++ does not provide a usable C++23 mode.\n"
        + "\n".join(errors)
    )

def run_subprocess(command, cwd_in):
    '''
    Executes a command and raises an error if it fails.
    Captures and prints the standard error output on failure.
    Returns the standard output on success.
    '''
    try:
        result = subprocess.run(
            command,
            cwd = cwd_in,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            text = True,
            check = True,
            shell = True
        )
        return result.stdout
    except subprocess.CalledProcessError as error:
        raise RuntimeError(
            f"Command failed: {command}\n"
            f"Working directory: {os.path.abspath(cwd_in)}\n"
            f"Exit code: {error.returncode}\n"
            f"stdout:\n{error.stdout or ''}\n"
            f"stderr:\n{error.stderr or ''}"
        ) from error
  
# def test_consistent(compare_file_list) -> None:
#     '''
#     Test if the output results are the same.

#     This function will write error log to `error_info.txt`.
#     Trying to support hybrid number of I/O files.
#     '''




    









