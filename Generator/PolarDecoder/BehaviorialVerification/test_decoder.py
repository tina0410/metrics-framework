import sys

_ORIGINAL_ARGV = sys.argv[:]
sys.argv = [sys.argv[0]]
from decoder import *
import os
import subprocess
import pytv
from pytv import convert
from pytv import moduleloader
sys.argv = _ORIGINAL_ARGV
from utils import run_iverilog_flow, merge_files, move_and_rename_file, run_cpp_flow, merge_2_files
from cpp_modules import ModuleConfig
moduleloader.set_naming_mode("SEQUENTIAL")
moduleloader.set_root_dir("RTL")
moduleloader.set_debug_mode(True)
import math
import pytest


def load_config(ConfigFileName="./config/config1.json"):
    # Load Configuration
    import json
    try:
        with open(ConfigFileName, 'r') as f:
            config = json.load(f)
        config_dict = {}
        config_dict['archi'] = config.get("Hardware Architecture", "TypeI")
        config_dict['algo'] = config.get("Decoding Algorithm", "MS")
        N = config.get("Code Length", 1024)
        M = config.get("Parallelism", 1024)
        width = config.get("Data Width",5)
        config_dict['N'] = N
        config_dict['M'] = M
        config_dict['width'] = width
        return config_dict
        
    except FileNotFoundError:
        print(f"Warning: Config file {ConfigFileName} not found. Using default parameters.")
        archi = "TypeI"
        algo = "MS"
        N = 1024
        M = 1024
        width = 5
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file {ConfigFileName}: {e}")
        return
    except Exception as e:
        print(f"Error loading config: {e}")
        return

config_files = ["./config/config1.json","./config/config2.json","./config/config3.json","./config/config4.json","./config/config5.json"]

@pytest.mark.parametrize("config_file_path", config_files)
def test_decoder(config_file_path):
    moduleloader.reset()
    moduleloader.disEnableWarning()
    test_no = int(config_file_path.split("/")[-1].split(".")[0][-1])
    RTL_folder = "RTL"+str(test_no)
    config_dict = load_config(config_file_path)
    algo = config_dict['algo']
    archi = config_dict['archi']
    width = config_dict['width']
    if width == 5:
        int_width = 3
        frac_width = 1
    elif width == 7:
        int_width = 4
        frac_width = 2
    elif width == 8:
        int_width = 4
        frac_width = 3
    elif width == 12:
        int_width = 3
        frac_width = 8
    N = config_dict['N']
    M = config_dict['M']
    K = round(N/2)
    # delete files in 'RTL' using os.remove()
    import os
    import subprocess
    root_dir = "./"
    test_case_dir = os.path.join(root_dir, "testcase")
    rtl_folder_path = os.path.join(test_case_dir, RTL_folder)
    run_iverilog = True
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.set_root_dir(rtl_folder_path)
    moduleloader.set_debug_mode(True)
    generated_file_dir = os.path.join(root_dir, "RTL", "RTL"+str(test_no))

    # generate verilog code and run iverilog code
    for file in os.listdir(rtl_folder_path):
        os.remove(os.path.join(rtl_folder_path, file))
    Moduletest(width=width, N=N, M=M, archi=archi, algo=algo, int_width=int_width, frac_width=frac_width, root_path=root_dir, testcase_name=f"BP Testcase{test_no}")
    merged_file_name = "BP_tb.v"
    # merge_files(rtl_folder_path, merged_file_name)
    merge_files(generated_file_dir, "designs.v")  # BP_tb.v (generated_file_dir)
    move_and_rename_file(generated_file_dir, rtl_folder_path, "designs.v", "designs.v")
    merge_2_files(rtl_folder_path, "designs.v", "test0000000001.v",merged_file_name)
    # move_and_rename_file()
    if (run_iverilog) :
        run_iverilog_flow(folder_path=rtl_folder_path)

    # run cpp behavioral simulation
    moduleloader.set_root_dir("tmp")
    ModuleConfig(data_width=width, frac_width=frac_width, n=N, k=K, LANGUAGE_MODE='cpp_header')
    move_and_rename_file('tmp','./include','Config0000000001.h','Config0000000001.h')
    command_compile = f"clang++ -std=c++23 -Iinclude -o3 -O3 bp_polar_decoder.cpp"
    command_execute = f"./3"
    run_cpp_flow(cwd_in=root_dir, command=command_compile)
    run_cpp_flow(cwd_in=root_dir, command=command_execute)

    # files to compare
    # input_file_name = f"u2N{N}K{K}INTDWT{int_width}FRACDWT{frac_width}MS.txt"
    input_file_name = f"u_route_log.txt"
    output_file_name = f"u2N{N}K{K}INTDWT{int_width}FRACDWT{frac_width}MS.txt"
    if run_iverilog:
        file_list = [os.path.join(root_dir, "comparison_files", input_file_name), os.path.join(root_dir,"output_files", "decoding_output.txt")]
    else:
        file_list = [os.path.join(root_dir, "comparison_files", input_file_name), os.path.join(root_dir,"input_files", output_file_name)]
    with open(file_list[0], 'r') as f_in, open(file_list[1], 'r') as f_out:
        input_data = f_in.read().split('\n')
        output_data = f_out.read().split('\n')
    # print(f"{input_data}")
    # print(f"{output_data}")
    # compare results
    test_passed = True
    for i in range(len(input_data)):
        if input_data[i] != output_data[i]:
            print(f"Mismatch at line {i+1}")
            print(f"Input: {input_data[i]}")
            print(f"Output: {output_data[i]}")
            # print failure in red
            print("\033[91m" + "Test failed" + "\033[0m")
            test_passed = False
            break
    else:
        # print success in green
        print("\033[92m" + "Test passed" + "\033[0m")
    assert(test_passed)
        




        
