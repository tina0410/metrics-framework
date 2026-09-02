# Description: A Pytest Frame
# Author: Jiayan Xu
# Author: LiPtP
# Author: Yifang Dai
# Date: 2025.3.12

import sys
import math
import os
import shutil
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
from tb_LSCE import *
from BehavModel_LSCE import *
import PyTU
import PyTB
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader 
import shutil 



# Testcase Definition
class Testcase:
    __test__ = False

    DUT_NAME = "LSCE"    
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
    
    def __init__(self, ConfigFileName:str, N_FRAMES=10):
        # Load Configuration
        import json
        
        try:
            with open(ConfigFileName, 'r', encoding='utf-8-sig') as f:
                config = json.load(f)
            
            # Load parameters from config
            N_T = config.get("Number of Transmit Antennas", 256)
            N_R = config.get("Number of Receiving Antennas", 16)
            P_T = config.get("Parallelism T", 16)
            P_R = config.get("Parallelism R", 4)
            
            # Load quantization types
            qu_y_config = config.get("Quantization format of Y", {"bitwidth": 16, "fractional width": 0, "signed": True})
            QU_Y = QuType(qu_y_config["bitwidth"], qu_y_config["fractional width"], qu_y_config["signed"])
            
            qu_p_config = config.get("Quantization format of P", {"bitwidth": 16, "fractional width": 0, "signed": True})
            QU_P = QuType(qu_p_config["bitwidth"], qu_p_config["fractional width"], qu_p_config["signed"])
            
            qu_h_config = config.get("Quantization format of H", {"bitwidth": 16, "fractional width": 0, "signed": True})
            QU_H = QuType(qu_h_config["bitwidth"], qu_h_config["fractional width"], qu_h_config["signed"])
            
            qu_m_v_config = config.get("Quantization format of M_V", {"bitwidth": 16, "fractional width": 0, "signed": True})
            QU_M_V = QuType(qu_m_v_config["bitwidth"], qu_m_v_config["fractional width"], qu_m_v_config["signed"])
            
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
            
            N_PIPELINES = config.get("Pipeline Stages ([Multiplication, Adder Tree])", [1, 1])
            CLOCK_PERIOD_NS = float(config.get("clock", {}).get("period_ns", 10.0))
            if not math.isfinite(CLOCK_PERIOD_NS) or CLOCK_PERIOD_NS <= 0:
                raise ValueError("clock.period_ns must be a finite value greater than zero")
        except FileNotFoundError:
            print(f"Warning: Config file {ConfigFileName} not found. Using default parameters.")
            # Use default parameters
            N_T = 256
            N_R = 16
            P_T = 16
            P_R = 4
            QU_Y = QuType(16, 0, True)
            QU_P = QuType(16, 0, True)
            QU_H = QuType(16, 0, True)
            QU_M_V = QuType(16, 0, True)
            QU_MODE = QuMode.TRN.TCPL
            OF_MODE = OfMode.WRP.TCPL
            N_PIPELINES = [1, 1]
            CLOCK_PERIOD_NS = 10.0
        
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in config file {ConfigFileName}: {e}")
            return
        
        except Exception as e:
            print(f"Error loading config: {e}")
            return
    
        self.N_T = N_T
        self.N_R = N_R
        self.P_T = P_T
        self.P_R = P_R
        self.QU_Y = QU_Y
        self.QU_P = QU_P
        self.QU_H = QU_H
        self.QU_M_V = QU_M_V
        self.QU_MODE = QU_MODE
        self.OF_MODE = OF_MODE
        self.N_PIPELINES = N_PIPELINES
        self.CLOCK_PERIOD_NS = CLOCK_PERIOD_NS
        self.N_FRAMES = N_FRAMES
        self.SeqNum = os.environ.get(
            "LSCE_CASE_ID", Path(ConfigFileName).stem.split("_case")[-1]
        )
    
    def display_info(self):
        '''
        Write the parameters you want to display in error_info.txt
        In most cases, only `info` requires modification.
        ''' 
        info = f"N_T: {self.N_T}, N_R: {self.N_R}, P_T: {self.P_T}, P_R: {self.P_R}, QU_Y: ({self.QU_Y.DWT}, {self.QU_Y.FRAC}, {self.QU_Y.isSigned}), QU_P: ({self.QU_P.DWT}, {self.QU_P.FRAC}, {self.QU_P.isSigned}), QU_H: ({self.QU_H.DWT}, {self.QU_H.FRAC}, {self.QU_H.isSigned}), QU_M_V: ({self.QU_M_V.DWT}, {self.QU_M_V.FRAC}, {self.QU_M_V.isSigned}), QU_MODE: {self.QU_MODE.cppType()}, OF_MODE: {self.OF_MODE.cppType()}, N_PIPELINES: {self.N_PIPELINES}, N_FRAMES: {self.N_FRAMES}\n"
        return info


def generate_testcase_spec(Testcase):
    selected_config = os.environ.get("LSCE_CONFIG_PATH")
    if selected_config:
        config_paths = [selected_config]
    else:
        config_file_path = "../configs"
        config_paths = [
            os.path.join(config_file_path, filename)
            for filename in sorted(os.listdir(config_file_path))
            if filename.endswith(".json")
        ]
    return [Testcase(ConfigFileName=path, N_FRAMES=10) for path in config_paths]


# -------------------------------User Settings------------------------------- #
# Testcase Range
testcase = generate_testcase_spec(Testcase)
@pytest.mark.parametrize("Testcase", testcase)

def test_my_module(request: pytest.FixtureRequest, Testcase:Testcase):
    print("TEST STARTED")
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
    # ------------------------------------------------------------------------------ #
    # Set working directory
    os.chdir(root_dir)
    test_num = f"Testcase{Testcase.SeqNum}"
    sim_root = Path(os.environ.get("LSCE_SIM_ROOT", "./sim")).resolve()
    design_rtl_root = Path(
        os.environ.get("LSCE_DESIGN_RTL_ROOT", "../RTL")
    ).resolve()
    tb_i_files_path = f"../../Input_Files/{test_num}"
    tb_o_files_path = f"../../Output_Files/{test_num}"
    cpp_i_files_path = f"../Input_Files/{test_num}"
    cpp_c_files_path = f"../Comparison_Files/{test_num}"
    compare_i_files_path = str(sim_root / "Input_Files" / test_num)
    compare_o_files_path = str(sim_root / "Output_Files" / test_num)
    compare_c_files_path = str(sim_root / "Comparison_Files" / test_num)
    log_files_path = str(sim_root / "Log_Files")
    # test_log_path = 
    # if not os.path.exists(o_files_path):
    #     os.makedirs(o_files_path)
    # if not os.path.exists(i_files_path):
    #     os.makedirs(i_files_path)
    # if not os.path.exists(c_files_path):
    #     os.makedirs(c_files_path)
    # if not os.path.exists(log_files_path):
    #     os.makedirs(log_files_path)

    for path in [compare_i_files_path, compare_o_files_path, compare_c_files_path, log_files_path]:
        os.makedirs(path, exist_ok=True)

    # Clear Files under ./sim/RTL
    folder_path = str(sim_root / "RTL" / test_num)

    

    # Generate RTL code & Testbench
    
    moduleloader.set_language_mode('VERILOG')
    moduleloader.set_root_dir(folder_path)
    moduleloader.disEnableWarning()
    moduleloader.set_naming_mode("SEQUENTIAL")

    verilog_run_flag = True
    error_record = []

    print(f"Genrating Testing RTL Code...")
    # -----------------------------User Settings------------------------------------ #
    ModuleTbLSCE(
        N_T=Testcase.N_T, N_R=Testcase.N_R, 
        P_T=Testcase.P_T, P_R=Testcase.P_R,
        QU_Y=Testcase.QU_Y, QU_P=Testcase.QU_P,
        QU_H=Testcase.QU_H, QU_M_V=Testcase.QU_M_V,
        QU_MODE=Testcase.QU_MODE, OF_MODE=Testcase.OF_MODE,
        N_PIPELINES=Testcase.N_PIPELINES,
        CLOCK_PERIOD_NS=Testcase.CLOCK_PERIOD_NS,
        input_file_dir=tb_i_files_path, output_file_dir=tb_o_files_path,
        N_FRAMES=Testcase.N_FRAMES
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
    cpp_include_root = sim_root / "CppModules" / "include"
    cpp_root = sim_root / "CppModules"
    moduleloader.set_root_dir(str(cpp_include_root))
    moduleloader.set_language_mode('CPP_HEADER')
    ModuleCppConfig()

    moduleloader.set_root_dir(str(cpp_root))
    moduleloader.set_language_mode('CPP')
    ModuleCppRun(
        N_T=Testcase.N_T, N_R=Testcase.N_R,
        P_T=Testcase.P_T, P_R=Testcase.P_R,
        QU_Y=Testcase.QU_Y, QU_P=Testcase.QU_P,
        QU_H=Testcase.QU_H, QU_M_V=Testcase.QU_M_V,
        QU_MODE=Testcase.QU_MODE, OF_MODE=Testcase.OF_MODE,
        N_PIPELINES=Testcase.N_PIPELINES,
        input_file_dir=cpp_i_files_path, comparison_file_dir=cpp_c_files_path,
        N_FRAMES=Testcase.N_FRAMES
    )
    
    cpp_config_file_name_gen = list(moduleloader.getParams(cpp_config_file_name_prefix)[-1].keys())[-1] + '.h'
    cpp_run_file_name_gen = list(moduleloader.getParams(cpp_run_file_name_prefix)[-1].keys())[-1] + '.cpp'
    # raise(ValueError)
    PyTB.move_and_rename_file(str(cpp_include_root), str(cpp_include_root), cpp_config_file_name_gen, cpp_config_file_name_dest)
    PyTB.move_and_rename_file(str(cpp_root), str(cpp_root), cpp_run_file_name_gen, cpp_run_file_name_dest)
    
    # Running cpp files to generate input and comparison files
    print(f"{PyTB.BLUE}Running cpp file to generate input and comparison files")
    
    cpp_compiler = os.environ.get("CXX") or shutil.which("clang++-20") or "clang++"
    cpp_compile_command = f'"{cpp_compiler}" {cpp_run_file_name_dest} -std=c++2b -Iinclude -oLSCE.out'
    cpp_run_command = "LSCE.out" if os.name == "nt" else "./LSCE.out"
    run_subprocess(cpp_compile_command, cwd_in=str(cpp_root))
    run_subprocess(cpp_run_command, cwd_in=str(cpp_root))
    
    # Collect all verilog files in ./RTL/Parameters{n}
    verilog_file_list = ''
    os.system("sync")
    
    for file in os.listdir(folder_path):
        if file.endswith('.v'):
            verilog_file_list += file + " "
    
    print(f"Running iverilog compiler...")

    iverilog_command = f"iverilog -o wave {verilog_file_list}"
    print(iverilog_command)
    run_subprocess(iverilog_command, cwd_in=folder_path)

    print(f"Running vvp...")
    vvp_command = f"vvp -n wave -lxt2"
    
    run_subprocess(vvp_command,cwd_in=folder_path)
    
    # print(f"Clearing directory {os.path.abspath(folder_path)}...")

    # for filename in os.listdir(folder_path):
    #     file_path = os.path.join(folder_path, filename)
    #     if os.path.isfile(file_path):
    #         os.remove(file_path)  
    # print('done.\n')
    # gtkwave
    # gtkwave_command = "gtkwave wave.vcd"
    # run_subprocess(gtkwave_command)
    # Run Comparison
    
    print(f"Running comparison...")

    # ------------------------------User Settings----------------------------------- #
    
    #------------------------ Comparison List --------------------------#
    compare_list = [
        (f"{compare_i_files_path}/i_Y.txt", f"{compare_o_files_path}/i_Y_out.txt"),
        (f"{compare_i_files_path}/i_P.txt", f"{compare_o_files_path}/i_P_out.txt"),
        (f"{compare_c_files_path}/o_H.txt", f"{compare_o_files_path}/o_H.txt")
    ]
    if Testcase.N_T / Testcase.P_T > 1:
        compare_list.append((f"{compare_i_files_path}/i_ctrl_stg.txt", f"{compare_o_files_path}/i_ctrl_stg_out.txt"))
    #-------------------------------------------------------------------#

    # Check for inconsistencies in binary files and raise warning
    clear_flag = True
    for file1, file2 in compare_list:
        with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
            if f1.read() != f2.read():
                print(f"\033[1;31;40mMISMATCH:\033[0m {file1} and {file2} are inconsistent.")
                clear_flag = False
            else:
                print(f"\033[1;32;40mSUCCESS:\033[0m {file1} and {file2} are consistent.")

    if (clear_flag):
        print("Results are consistent. \033[1;32;40mVerification Success!\033[0m")
    else:
        print("Results are not consistent. \033[1;31;40mVerfication Failed!\033[0m")
        err_info = Testcase.display_info()
        PyTB.Log.write_error_info(log_files_path, [f"ERROR IN TEST CASE \n:\033[0m {err_info}"])

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




    




