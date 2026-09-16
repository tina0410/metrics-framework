# Description: A Pytest Frame
# Author: Jiayan Xu
# Author: LiPtP
# Date: 2025.2.22

import sys
import os 
# from tests.parameters import Parameters
from os.path import dirname, abspath
# sys.path.append('/home/xjy-ubuntu/docs/AutoGen/VeriTests')
sys.path.append(dirname(dirname(__file__)))
sys.path.append(dirname(__file__))

import random
import pytest
import os
from pathlib import Path
import subprocess
from tb_Sub import *
from BehavModel_Sub import *
import PyTU
import PyTB
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader  



# Testcase Definition
class Testcase:

    DUT_NAME = "Sub"    
    '''
    Name of DUT, the naming format is the same as the module folder name.
    '''
    TB_NAME_PREFIX = f"Tb{DUT_NAME}"
    '''
    Prefix of Testbench Name. e.g. **TbAdd**0000000001.v. Should not be modified.
    '''
    CPP_CONFIG_FILE_NAME_PREFIX = f"CppConfig"    
    CPP_RUN_FILE_NAME_PREFIX = "CppRun"
    CPP_CONFIG_FILE_NAME_DEST = "config.h"
    CPP_RUN_FILE_NAME_DEST = f"{DUT_NAME}.cpp"
    ROOT_DIR = '.'
    
    def __init__(self, qu_type_in_1:PyTU.QuType, qu_type_in_2:PyTU.QuType, qu_type_out:PyTU.QuType, qu_mode, of_mode, if_rst_n, n_clk, n_frames):
        '''
        You need to declare **all** parameters you want to test in test_xxx function.
        '''
        self.QU_IN_1 = qu_type_in_1
        self.QU_IN_2 = qu_type_in_2
        self.QU_OUT = qu_type_out
        self.IF_RST_N = if_rst_n
        self.N_CLK = n_clk
        self.N_FRAMES = n_frames
        self.QU_MODE = qu_mode
        self.OF_MODE = of_mode

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
        signed_in_2 = signed_str[self.QU_IN_2.IF_SIGNED]
        signed_out = signed_str[self.QU_OUT.IF_SIGNED]
        info = f"QU_IN_1({self.QU_IN_1.DWT}, {self.QU_IN_1.FRAC}, {signed_in_1})\n" + f"QU_IN_2({self.QU_IN_2.DWT}, {self.QU_IN_2.FRAC}, {signed_in_2})\n" + f"QU_OUT({self.QU_OUT.DWT}, {self.QU_OUT.FRAC}, {signed_out})\n" + f"QU_MODE: {QuMode_str}    OF_MODE: {OfMode_str}\n" + f"IF_RST_N: {self.IF_RST_N}    N_CLK: {self.N_CLK}\n"
        return info
    
            
# At the beginning of the test, clear the generated files
os.system("rm -rf ./sim/RTL/*")
os.system("rm -rf ./sim/Log_Files/*")

def generate_testcase_specific_value_case1(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n_range = [[False, False, True, False]], 
        dwt_in_range_1 = [7], 
        dwt_in_range_2 = [5], 
        dwt_out_range = [4],
        frac_in_range_1 = [4],
        frac_in_range_2 = [7],  
        frac_out_range = [3], 
        if_signed_in_range_1 = [True],
        if_signed_in_range_2 = [True],
        if_signed_out_range = [True], 
        qu_mode_range = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode_range = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN], 
        n_frames_range = [100], 
        n_clk_range = [4]
    )
    
    testcase = generator.generate_testcases(Testcase)
    
    return testcase

# -------------------------------User Settings------------------------------- #
# Testcase Range
testcase = generate_testcase_specific_value_case1(Testcase)
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
    # IF_ENABLE = Parameters.IF_ENABLE
    QU_OUT = Testcase.QU_OUT
    N_CLK = Testcase.N_CLK
    IF_RST_N = Testcase.IF_RST_N
    QU_MODE= Testcase.QU_MODE
    OF_MODE= Testcase.OF_MODE
    N_FRAMES = Testcase.N_FRAMES
    Log=PyTB.Log(if_rst_n= IF_RST_N, qu_type_in_1=QU_IN_1, qu_type_in_2=QU_IN_2, qu_type_out=QU_OUT, qu_mode=QU_MODE, of_mode=OF_MODE, n_frames=N_FRAMES , n_clk=N_CLK)
    # ------------------------------------------------------------------------------ #
    # Set working directory
    os.chdir(root_dir)
    o_files_path = "./sim/Output_Files"
    i_files_path = "./sim/Input_Files"
    c_files_path = "./sim/Comparison_Files"
    log_files_path = "./sim/Log_Files"
    # test_log_path = 
    if not os.path.exists(o_files_path):
        os.makedirs(o_files_path)
    if not os.path.exists(i_files_path):
        os.makedirs(i_files_path)
    if not os.path.exists(c_files_path):
        os.makedirs(c_files_path)
    if not os.path.exists(log_files_path):
        os.makedirs(log_files_path)

    # Clear Files under ./sim/RTL
    test_num = request.node.callspec.id
    folder_path = f'./sim/RTL/{test_num}'

    

    # Generate RTL code & Testbench
    
    
    moduleloader.set_language_mode('VERILOG')
    moduleloader.set_root_dir(folder_path)
    moduleloader.disEnableWarning()
    moduleloader.set_naming_mode("SEQUENTIAL")

    verilog_run_flag = True
    error_record = []

    print(f"Genrating Testing RTL Code...")

    # -----------------------------User Settings------------------------------------ #
    ModuleTbSub(
        QU_IN_1 = QU_IN_1,
        QU_IN_2=QU_IN_2,
        QU_OUT = QU_OUT, 
        N_CLK = N_CLK, 
        IF_RST_N = IF_RST_N, 
        QU_MODE=QU_MODE, 
        OF_MODE=OF_MODE, 
        N_FRAMES=N_FRAMES
        )
    print('done\n')
    moduleloader.reset()
    # ------------------------------------------------------------------------------- #
    

    # Generate cpp config and run files
    # CAUTION !!!!!! This may overwrite the existing files in the directory !!!!!!
    print(f"Generating cpp config and run files")
    moduleloader.set_root_dir('./sim/CppModules/include')
    moduleloader.set_language_mode('CPP_HEADER')

    # PyTB.delete_file('./sim/CppModules/include',cpp_config_file_name_dest)
    # PyTB.delete_file('./sim/CppModules', cpp_run_file_name_dest)

    
    ModuleCppConfig(QU_IN_1=QU_IN_1, QU_IN_2=QU_IN_2, QU_OUT=QU_OUT, QU_MODE=QU_MODE, OF_MODE=OF_MODE)
    moduleloader.set_root_dir('./sim/CppModules')
    moduleloader.set_language_mode('CPP')
    ModuleCppRun(N_FRAMES=N_FRAMES)

    # Get the names of generated cpp files
    cpp_config_file_name_gen = list(moduleloader.getParams(cpp_config_file_name_prefix)[-1].keys())[-1] + '.h'
    cpp_run_file_name_gen = list(moduleloader.getParams(cpp_run_file_name_prefix)[-1].keys())[-1] + '.cpp'
    # raise(ValueError)
    PyTB.move_and_rename_file('./sim/CppModules/include', './sim/CppModules/include', cpp_config_file_name_gen, cpp_config_file_name_dest)
    PyTB.move_and_rename_file('./sim/CppModules', './sim/CppModules', cpp_run_file_name_gen, cpp_run_file_name_dest)
    
    # Running cpp files to generate input and comparison files
    print(f"{PyTB.BLUE}Running cpp file to generate input and comparison files")
    
    cpp_compile_command = f"clang++ {cpp_run_file_name_dest} -std=c++23 -Iinclude -ofxp2.out"
    cpp_run_command = "./fxp2.out"
    run_subprocess(cpp_compile_command, cwd_in="./sim/CppModules")
    run_subprocess(cpp_run_command, cwd_in="./sim/CppModules")

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
        ("./sim/Input_Files/sub_i_data_1.txt",
         "./sim/Input_Files/sub_i_data_2.txt",
         "./sim/Comparison_Files/sub_o_data.txt", 
         "./sim/Output_Files/sub_o_data.txt"),
        ]
    
    clear_flag = True
    for file0, file1, file2, file3 in compare_file_list:
         file0_tmp = file0
         file1_tmp = file1
         file2_tmp = file2
         file3_tmp = file3
         with open(file0, 'r', encoding='utf-8') as file0, open(file1, 'r', encoding='utf-8') as file1, open(file2, 'r', encoding='utf-8') as file2, open(file3, 'r', encoding='utf-8') as file3:
            line_number = 0
            for line0, line1, line2, line3 in zip(file0, file1, file2, file3):
                line_number += 1
                if line2.strip() != line3.strip():
                    dec_num0,msg= PyTB.binary_complement_to_decimal(line0.strip(),is_signed = QU_IN_1.IF_SIGNED)
                    dec_num1,msg= PyTB.binary_complement_to_decimal(line1.strip(),is_signed = QU_IN_2.IF_SIGNED)
                    dec_num2,msg= PyTB.binary_complement_to_decimal(line2.strip(),is_signed = QU_OUT.IF_SIGNED)
                    dec_num3,msg = PyTB.binary_complement_to_decimal(line3.strip(),is_signed = QU_OUT.IF_SIGNED)
                    clear_flag = False
                    if verilog_run_flag:
                        error_record.append(f"{file0_tmp}:{line0.strip()}(d{dec_num0}), {file1_tmp}:{line1.strip()}(d{dec_num1}), {file2_tmp}:{line2.strip()}(d{dec_num2}), {file3_tmp}:{line3.strip()}(d{dec_num3}) \n")

    if (clear_flag):
        print("Results are consistent. \033[1;32;40mVerification Success!\033[0m")
    else:
        print("Results are not consistent. \033[1;31;40mVerfication Failed!\033[0m")
        err_info = Testcase.display_info()
        print(f"\033[1;31;40mERROR IN TEST CASE \n:\033[0m {err_info}")
        Log.write_error_info(log_files_path, error_record)

    assert clear_flag == True
    print(f"{PyTB.BLUE}Done!")
    # ------------------------------------------------------------------------------ #

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
        print(f"\033[31mError: \033[0m{error.stderr}")
        raise error
  
# def test_consistent(compare_file_list) -> None:
#     '''
#     Test if the output results are the same.

#     This function will write error log to `error_info.txt`.
#     Trying to support hybrid number of I/O files.
#     '''




    




