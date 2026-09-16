# coding = utf-8
# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1

from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

import sys
import os
from os.path import dirname, abspath
sys.path.append(dirname(dirname(__file__)))
sys.path.append(dirname(__file__))

import itertools
import PyTU
import os
import shutil
from contextlib import ExitStack

# define colors
BLUE = "\033[1;34m"
RED = "\033[1;33m"
RESET = "\033[0m"



# Initialize the signals
@convert
def Moduledrive_clk(port = "clk", period = 10):
    '''
    Clock drive for the testbench. It has a default period of 10.
    '''
    # port is the name of generated clk signal, period is the clk period
    period_half = round(period / 2)
    #/ initial
    #/ begin
    #/     `port` = 0;
    #/      forever #`period_half`  `port` <= ~`port`;
    #/ end
    pass

# initialize ports
@ convert
def ModuleInitialize(ports: list):
    '''
    Initialize the input ports to 0.
    '''
    #/ initial begin
    for port in ports:
        #/ `port` <= 'b0;
        pass
    #/ end
    pass


# drive arst signal
@ convert
def Moduledrive_arst(port="arst_n", clk="clk", start=1, last=10):
    '''
    Describes an Asynchronous Reset Drive.
    The reset signal is triggered after `start` negative clock edges and remains active for `last` negative clock edges.
    '''
    #/ initial
    #/ begin
    #/     `port` <= 1;
    #/     repeat (`start`) @(negedge `clk`);
    #/     `port` <= 0;
    #/     repeat (`last`) @(negedge `clk`);
    #/     `port` <= 1;
    #/ end
    pass



@convert
def Moduledrive_input_signal(ports:list, files:list, clk:str="clk", en_name: str= "en", if_en :str= False, n_latency:int=30, if_end: bool=False, end_wait:int=100, input_file_dir="./sim/Input_Files", **kwargs):
    '''
        Create Excitation for Input ports via File Ports

        Args:
            ports (list): The list of excitation variable names.
            files (list): The list of excitation variable files. Require same length as ports.
            clk (str, optional): Reference clk. Defaults to "clk".
            n_latency (int, optional): Delay before excitation. Defaults to 30.
            en_name (str, optional): The name of the enable signal. Defaults to single "en".
            if_en (bool, optional): If True, the enable signal will be excited. Defaults to False.
            if_end (bool, optional): If True, $finish will be added. Defaults to False.
            end_wait (bool, optional): wait X clks before finish. Defaults to 100.
        Modes (parsed with kwargs):
            Mode A1:
                n_cycle (int): The excitation cycle.
            Mode A2:
                n_cycle (int): The excitation cycle.
                n_excites (int): The maximum number of excites.
                grp (str, optional): The excitation group iterable name.
            Mode B:
                n_stamps (list): The list of excitation time stamps.
            Mode C:
                n_div_stamps (list): The list of excitation time stamp seperations.
    '''
    modes = {
        'A2': ['n_cycle', 'n_excites'],
        'A1': ['n_cycle'],
        'B': ['n_stamps'],
        'C': ['n_div_stamps']
    }

    # Check if the ports and files are of the same length
    if len(ports) != len(files):
        raise ValueError("The length of ports and files must be the same.")

    # Check if the en_names and if_en are of the same length
    # if len(if_en) != len(en_names):
    #     raise ValueError("The length of if_en and en_names must be the same.")

    # seen = {}
    # for k, en in enumerate(en_names):
    #         if en in seen:
    #             if seen[en] != if_en[k]:
    #                 raise ValueError(f"Conflict for '{en}': previously {seen[en]}, now {if_en[k]}")
    #             continue
    #         seen[en] = if_en[k]

    mode = None
    for mode_type, required_args in modes.items():
        if all(arg in kwargs for arg in required_args):
            mode = mode_type
            break

    if mode is None:
        extra_args = set(kwargs.keys()) - set(arg for args in modes.values() for arg in args)
        if extra_args:
            raise ValueError(f"Unexpected arguments: {', '.join(extra_args)}")
        else:
            raise ValueError("No matching mode found. Missing required arguments.")

    feof_conditions = " && ".join(f"!$feof({port}_dat)" for port in ports)
    print("Current Input mode is set to: ", f"{mode}")

    #/ // Print the header
    for port in ports:
        #/ integer `port`_dat;   // file handle by $fopen
        #/ integer `port`_st;   // status of $fscanf
        pass

    if mode == "A1":
        #/ initial begin
        #/ repeat (`n_latency`) @(posedge `clk`);
        for port, file in zip(ports, files):
            #/ `port`_dat = $fopen("`input_file_dir`/`file`", "r");
            pass
        #/ while (`feof_conditions`) begin
        for port in ports:
            #/ `port`_st = $fscanf(`port`_dat, "%b\\n", Input_`port`);
            pass
        #/ repeat (`kwargs['n_cycle']`) @(posedge `clk`);
        for j, port in enumerate(ports):
                #/ `port` <= Input_`port`;
                pass
        if if_en:
            #/ `en_name` <= 1'b1;
            pass
        #/ end
    elif mode == "A2":
        grp = kwargs.get("grp", "group") # make it optional
        lim = kwargs['n_excites']
        #/ integer iter_`grp`;
        #/ initial begin
        #/ repeat (`n_latency`) @(posedge `clk`);
        for port, file in zip(ports, files):
            #/ `port`_dat = $fopen("`input_file_dir`/`file`", "r");
            pass
        #/
        #/ for (iter_`grp` = 0; iter_`grp` < `lim`; iter_`grp` = iter_`grp` + 1) begin
        #/ if (`feof_conditions`) begin
        for port in ports:
            #/ `port`_st = $fscanf(`port`_dat, "%b\\n", Input_`port`);
            pass
        #/ repeat (`kwargs['n_cycle']`) @(posedge `clk`);
        for j, port in enumerate(ports):
                #/ `port` <= Input_`port`;
                pass
        if if_en:
            #/ `en_name` <= 1'b1;
            pass
        #/ end  // end if
        #/ end  // end for
    elif mode == "B":
        # grp = kwargs['grp']
        #/ initial begin
        #/ repeat (`n_latency`) @(posedge `clk`);
        for port, file in zip(ports, files):
            #/ `port`_dat = $fopen("`input_file_dir`/`file`", "r");
            pass
        #/
        for i, n_stamp in enumerate(kwargs['n_stamps']):
            #/ if (`feof_conditions`) begin
            for port in ports:
                #/ `port`_st = $fscanf(`port`_dat, "%b\\n", Input_`port`);
                pass
            #/ end
            if i == 0:
                #/ repeat (`n_stamp`) @(posedge `clk`);
                pass
            else:
                #/ repeat (`kwargs['n_stamps'][i]` - `kwargs['n_stamps'][i-1]`) @(posedge `clk`);
                pass
            for j, port in enumerate(ports):
                #/ `port` <= Input_`port`;
                pass
            if if_en:
                #/ `en_name` <= 1'b1;
                pass
    elif mode == "C":
        #/ initial begin
        #/ repeat (`n_latency`) @(posedge `clk`);
        for port, file in zip(ports, files):
            #/ `port`_dat = $fopen("`input_file_dir`/`file`", "r");
            pass
        #/
        for i, n_div_stamp in enumerate(kwargs['n_div_stamps']):
            #/ if (`feof_conditions`) begin
            for port in ports:
                #/ `port`_st = $fscanf(`port`_dat, "%b\\n", Input_`port`);
                pass
            #/ end
            #/ repeat (`n_div_stamp`) @(posedge `clk`);
            for j, port in enumerate(ports):
                #/ `port` <= Input_`port`;
                pass
            if if_en:
                #/ `en_name` <= 1'b1;
                pass
    for port in ports:
        #/ $fclose(`port`_dat);
        pass
    if if_end:
        #/ repeat (`end_wait`) @(posedge `clk`);
        #/ $finish;
        pass
    #/ end


@convert
def ModuledumpMDA(name="o_data_MDA", handle="o_data_MDA_handle", MDAsize=[8,4,2], n_latency=0, if_end=False, end_wait=40, clk="clk", en="en", output_file_dir = "./sim/Output_Files", **kwargs):
    """
    Dump MDA Variables to {output_file_dir}/{name}.txt. It is implemented because iverilog does not support MDA dump.
    MDA is a multi-dimensional array, which is a list of lists.
    The dump is done in a loop, and the MDA is indexed by the loop variable.

    Arguments:
         name: str - Dump variable name.
         handle: str - Dump variable handle.
         MDAsize: list - Dump MDA size.
         n_latency: int (optional) - The latency before dump. Defaults to 0.
         if_end: bool (optional) - If True, the dump will end with a $finish statement. Defaults to False.
         end_wait: int (optional) - How many clks to wait before end. Defaults to 40.
         clk: str (optional) - Reference clk. Defaults to "clk".
         en: str (optional) - Reference en. Defaults to "en".
         kwargs: dict - Additional parameters containing mode-specific arguments.
    """
    modes = {
        'A': ['n_cycle', 'n_dump'],
        'B': ['n_stamps'],
        'C': ['n_div_stamps']
    }

    mode = next((m for m, args in modes.items() if all(arg in kwargs for arg in args)), None)

    if mode is None:
        extra_args = set(kwargs.keys()) - set(arg for args in modes.values() for arg in args)
        if extra_args:
            raise ValueError(f"Unexpected arguments: {', '.join(extra_args)}")
        raise ValueError("No matching mode found. Missing required arguments.")

    L_name = n_latency
    C_name = kwargs.get('n_cycle', 0)
    N_name = kwargs.get('n_dump', 0)
    print("Current Output mode is set to: ", f"{RED}{mode}{RESET}")
    #/ ///======== `name` Check ========///
    #/ reg `name`_out_indicator;
    #/ integer iter_`name`;
    #/ integer `name`_dat;
    for l in range(len(MDAsize)):
        #/ integer MDA`name`_i`l`;
        pass
    #/ initial begin
    #/     @(posedge `en`);
    #/     @(posedge `clk`); // for balance
    #/     `name`_dat = $fopen("`output_file_dir`/`name`.txt", "w");
    #/     `name`_out_indicator = 0;
    if L_name:
        #/     repeat (`L_name`) @(posedge `clk`);
        pass

    # Mode-based printing
    if mode == "A":
        #/     for (iter_`name` = 0; iter_`name` < `N_name`; iter_`name` = iter_`name` + 1) begin
        pass
    elif mode == "B":
        for i, n_stamp in enumerate(kwargs['n_stamps']):
            #/     repeat (`n_stamp if i == 0 else kwargs['n_stamps'][i] - kwargs['n_stamps'][i-1]`) @(posedge `clk`);
            pass
    elif mode == "C":
        for n_div_stamp in kwargs['n_div_stamps']:
            #/     repeat (`n_div_stamp`) @(posedge `clk`);
            pass
    #/     `name`_out_indicator = 0;
    pass

    curr_indent = "    "
    curr_index = "".join(f"[MDA{name}_i{l}]" for l in range(len(MDAsize)))

    for l, size in reversed(list(enumerate(MDAsize))):
        #/ `curr_indent`for (MDA`name`_i`l` = 0; MDA`name`_i`l` < `size`; MDA`name`_i`l` = MDA`name`_i`l` + 1) begin
        curr_indent += "    "
    #/ `curr_indent`$fwrite(`name`_dat, "%b", `handle + curr_index`);

    for _ in range(len(MDAsize)):
        curr_indent = curr_indent[:-4]
        #/ `curr_indent`end

    #/     `name`_out_indicator = 1;
    #/     $fwrite(`name`_dat, "\\n");

    if mode == "A":
        #/     repeat (`C_name`) @(posedge `clk`);
        #/     end
        pass

    #/     $fclose(`name`_dat);
    if if_end:
        #/     repeat(`end_wait`) @(posedge `clk`);
        #/     $finish;
        pass
    #/ end
    pass

@convert
def Moduledump( names, handles, n_latency = 0, if_end = False, end_wait = 40, clk = "clk", en = "en", output_file_dir = "./sim/Output_Files", **kwargs):
    '''
    Dump Variables to a file.
    Args:
        names (list): The list of dump variable names, which is the dumped file name without suffixes.
        handles (list): The list of dump variable handles, which is the content to dump.
        n_latency (int, optional): The latency before dump. Defaults to 0. This value will be the interval between en=1 and dump.
        output_file_dir (str, optional): The directory to store the dumped files. Defaults to "./sim/Output_Files".
        if_end (bool, optional): If True, the dump will end with a $finish statement. Defaults to False.
        end_wait (int, optional): How many clks to wait before end. Defaults to 40.
        clk (str, optional): Reference clk. Defaults to "clk".
        en (str, optional): Reference en. Defaults to "en". It defines the zero time reference of the output.
        grp (str, optional): The dump variable group name. Defaults to "group_dump".
        kwargs(dict, compulsory):
        Mode A:
            n_cycle (int): The number of cycles before dump.
            n_dump (int): The number of dumps.
        Mode B:
            n_stamps (list): The list of dump time stamps.
        Mode C:
            n_div_stamps (list): The list of dump time stamp separations.
    '''

    modes = {
        'A': ['n_cycle', 'n_dump'],
        'B': ['n_stamps'],
        'C': ['n_div_stamps']
    }
    mode = None
    for mode_type, required_args in modes.items():
        if all(arg in kwargs for arg in required_args):
            mode = mode_type
            break
    if mode is None:
        extra_args = set(kwargs.keys()) - set(arg for args in modes.values() for arg in args)
        if extra_args:
            raise ValueError(f"Unexpected arguments: {', '.join(extra_args)}")
        else:
            raise ValueError("No matching mode found. Missing required arguments.")
    print("Current Output mode is set to: ", f"{RED}{mode}{RESET}")


    if len(names) != len(handles):
        raise ValueError("The length of ports and files must be the same.")

    grp = kwargs.get("grp", "dump_group") # make it optional
    L_grp = n_latency if n_latency != 0 else None
    C_grp = kwargs.get('n_cycle', 0)
    N_grp = kwargs.get('n_dump', 0)
    # _dat: name of storage file
    #/ ///======== `grp` Check ========///
    #/ reg `grp`_out_indicator;
    #/ integer iter_`grp`;
    for name in names:
        #/ integer `name`_dat;
        pass
    #/ initial begin

    #/ // wait for enable and clock
    #/ @(posedge `en`);
    #/ @(posedge `clk`); // for balance


    if n_latency != 0:
        #/ repeat (`L_grp`) @(posedge `clk`);
        pass
    for name in names:
        #/ `name`_dat = $fopen("`output_file_dir`/`name`.txt", "w");
        pass
    #/ `grp`_out_indicator = 0;


    if mode == "A":
        #/ for (iter_`grp` = 0; iter_`grp` < `N_grp`; iter_`grp` = iter_`grp` + 1) begin
        #/ `grp`_out_indicator = 0;
        for name, handle in zip(names, handles):
            #/ $fdisplay(`name`_dat, "%b", `handle`);
            pass
        #/ `grp`_out_indicator = 1;
        #/ repeat (`C_grp`) @(posedge `clk`);
        #/ end
        pass
    elif mode == "B":
        for i, n_stamp in enumerate(kwargs['n_stamps']):
            if i == 0:
                #/ repeat (`n_stamp`) @(posedge `clk`);
                pass
            else:
                #/ repeat (`kwargs['n_stamps'][i]` - `kwargs['n_stamps'][i-1]`) @(posedge `clk`);
                pass
            #/ `grp`_out_indicator = 0;
            for name, handle in zip(names, handles):
                #/ $fdisplay(`name`_dat, "%b\\n", `handle`);
                pass
            #/ `grp`_out_indicator = 1;
    elif mode == "C":
        for i, n_div_stamp in enumerate(kwargs['n_div_stamps']):
            #/ repeat (`n_div_stamp`) @(posedge `clk`);
            #/ `grp`_out_indicator = 0;
            for name, handle in zip(names, handles):
                #/ $fdisplay(`name`_dat, "%b\\n", `handle`);
                pass
            #/ `grp`_out_indicator = 1;
            pass
    for name in names:
        #/ $fclose(`name`_dat);
        pass
    if if_end:
        #/ repeat(`end_wait`) @(posedge `clk`);
        #/ $finish;
        pass
    #/ end
    pass

@ convert
def Moduledump_waveform(dump_name:str, tb_name:str, simulator:str):
    '''
    Dump the testbench waveform to a vcd file (Icarus Verilog Format).
    Args:
        simulator (str): The simulator name. Currently only "iverilog" is supported.
        dump_name (str): The name of the dump file without file extension.
        tb_name (str): The name of the testbench.
    '''
    match simulator:
        case "iverilog":
            #/ initial begin
            #/     $dumpfile("`dump_name`.vcd");
            #/     $dumpvars(0, `tb_name`);
            #/ end
            pass
        case _:
            raise ValueError(f"Unsupported simulator: {simulator}.")


def calc_qublas_dwt(QU_VAR):
    '''
    Used in BahavModel to calculate IntBits and FracBits of a Qu Object.
    '''
    dwt = QU_VAR.DWT
    dwt_frac = QU_VAR.FRAC
    if (QU_VAR.IF_SIGNED):
        dwt_int_frac = dwt - 1
    else:
        dwt_int_frac = dwt
    dwt_int = dwt_int_frac - dwt_frac
    return dwt_int, dwt_frac


def int_to_hex_with_length(num):
    '''
    Used in test_xxx.py to convert integer to hex with fixed length.
    '''
    hex_value = hex(num)[2:]
    hex_value = hex_value.zfill(10)
    return str(hex_value)


def delete_file(directory,file_name):
    for root, dirs, files in os.walk(directory):
        if file_name in files:
            file_path = os.path.join(root, file_name)
            try:
                os.remove(file_path)
                print(f"Deleted: {file_path}")
            except Exception as e:
                print(f"Error deleting file {file_path} : {e}")



def move_and_rename_file(source_dir, target_dir, old_filename, new_filename):
    '''
    Used in test_xxx.py to move and rename files.
    '''
    source_file_path = os.path.join(source_dir, old_filename)
    target_file_path = os.path.join(target_dir, new_filename)
    try:
        shutil.move(source_file_path, target_file_path)
        print(f"Moving {old_filename} to {target_dir} and renaming it as {new_filename}")
    except FileNotFoundError:
        print(f"File {old_filename} not found in {source_dir}")
    except Exception as e:
        print(f"Error in Moving {old_filename} to {target_dir} and renaming it as {new_filename} : {e}")


# Newest Version
class Log:
    def __init__(self, compare_file_list:list, log_dir:str = "./sim/Log_Files", log_file_name:str = "error_info.txt"):
        self.compare_file_list = compare_file_list
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.log_file = os.path.join(log_dir, log_file_name)

    def compare_files_and_log(self, is_signed, verilog_run_flag):
        """
        Compare the last two files in `compare_file_list` line by line and log the errors in binary and decimal format.

        Args:
            compare_file_list (list[str]): List of file paths to compare.
            is_signed (list): List of PyTU.QuType.IF_SIGNED objects corresponding to each file.
            verilog_run_flag (bool): Flag to determine if errors should be logged.

        Returns:
            clear_flag (bool): True if all files match, False otherwise.
            error_record (list): List of error messages if mismatches are found.
        """
        clear_flag = True
        error_record = []
        filelist:list[str] = self.compare_file_list

        if len(filelist) < 2:
            raise ValueError("At least two files are required for comparison.")


        with ExitStack() as stack:
            file_objects = [stack.enter_context(open(file, 'r', encoding='utf-8')) for file in filelist]
            line_number = 0
            for lines in zip(*file_objects):
                line_number += 1
                stripped_lines = [line.strip() for line in lines]
                if stripped_lines[-2] != stripped_lines[-1]:  # Compare the last two files
                    decimal_values = []
                    for i, line in enumerate(stripped_lines):
                        dec_num, _ = self.binary_complement_to_decimal(line, is_signed[i])
                        decimal_values.append(dec_num)
                    clear_flag = False
                    if verilog_run_flag:
                        error_message = ", ".join(
                            f"{filelist[i]}:{stripped_lines[i]}(d{decimal_values[i]})"
                            for i in range(len(filelist))
                        )
                        error_record.append(f"{error_message}\n")

        return clear_flag, error_record

    @staticmethod
    def binary_complement_to_decimal(binary_str, is_signed=False):
        binary_str = binary_str.strip()
        if not binary_str:
            return None, "Empty string"

        length = len(binary_str)
        num = int(binary_str, 2)

        if is_signed and binary_str[0] == '1':
            num -= (1 << length)

        return num, "Success"


    def write_error_info(self, Testcase, error_record):
        info = Testcase.display_info()
        print(f"\033[1;31;40mERROR IN TEST CASE \n:\033[0m {info}")
        # write error info to log file
        with open(self.log_file, "a") as f:
            f.write(f"============================Test Case============================\n")
            f.write(info)
            f.write(f"=================================================================\n")
            f.write(f"Recorded Errors:\n" )
            for line in error_record:
                f.write(line)
            f.write(f"=================================================================\n\n")

    @staticmethod
    def clear_error_info(log_file:str):
        with open(log_file, "w") as f:
            f.write("")


class TestcaseGenerator:
    def __init__(self, **param_ranges):
        self.param_ranges = param_ranges

    def generate_testcases(self, Testcase):
        regular_params = {}
        qu_type_params = {}

        for param_name, param_values in self.param_ranges.items():
            if param_name.startswith(("dwt_", "frac_", "if_signed_")):

                parts = param_name.rsplit("_", 2)
                key = parts[0]
                qu_type_name = "_".join(parts[1:])
                if qu_type_name not in qu_type_params:
                    qu_type_params[qu_type_name] = {}
                qu_type_params[qu_type_name][key] = param_values
            else:

                regular_params[param_name] = param_values


        testcases = []
        for regular_values in itertools.product(*regular_params.values()):
            regular_kwargs = dict(zip(regular_params.keys(), regular_values))


            qu_type_combinations = []
            for qu_type_name, qu_type_param_ranges in qu_type_params.items():
                qu_type_combinations.append(
                    itertools.product(*qu_type_param_ranges.values())
                )


            for qu_type_values in itertools.product(*qu_type_combinations):
                testcase_kwargs = regular_kwargs.copy()


                for i, qu_type_name in enumerate(qu_type_params.keys()):
                    qu_type_args = qu_type_values[i]
                    testcase_kwargs[f"qu_type_{qu_type_name}"] = PyTU.QuType(*qu_type_args)

                testcases.append(Testcase(**testcase_kwargs))

        return testcases
