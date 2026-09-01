# coding = utf-8
# Date: 2025.4.2
# Author: LiPtP
# Author: Yifang Dai
# *Original Version by Jiayan Xu
'''
Here defines basic elements of a testbench, where you can use them in editing a testbench function. 

In general cases, no modifications should be applied to this module.
'''
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

import sys
import os 
# from tests.parameters import Parameters
from os.path import dirname, abspath
# sys.path.append('/home/xjy-ubuntu/docs/AutoGen/VeriTests')
sys.path.append(dirname(dirname(__file__)))
sys.path.append(dirname(__file__))

import pytest
import itertools
import PyTU
try:
    import pyverilog
    from pyverilog.vparser.parser import parse
except ModuleNotFoundError:
    pyverilog = None
    parse = None
import os
import shutil
from datetime import datetime
import subprocess

# define colors
BLUE = "\033[1;34m"
RED = "\033[1;33m"
RESET = "\033[0m"


# Declare the required ports
@ convert 
def ModuleDecl(input_ports, output_ports):
    '''
    Declaration of involved ports in Testbench.
    '''
    #/ // IO ports declaration
    for input_port in input_ports:
        if input_port.width is None:
            #/ reg `input_port.name`;
            pass
        else:
            #/ reg [`input_port.width`-1:0] `input_port.name`;
            pass
    for output_port in output_ports:
        if output_port.width is None:
            #/ wire `output_port.name`;
            pass
        else:
            #/ wire [`output_port.width`-1:0] `output_port.name`;
            pass

    #/ // File buffer declaration
    for input_port in input_ports:
        if input_port.width is None:
            #/ reg  Input_`input_port.name`_dat;
            pass
        else:
            #/ reg [`input_port.width`-1:0] Input_`input_port.name` ;
            pass

    #/ // Input ready and Output ready Indicators
    #/ reg INPUT_RDY;
    #/ reg OUTPUT_RDY;

    



# Initialize the signals
@convert
def Moduledrive_clk(port = "clk", period = 10):
    '''
    Clock drive for the testbench. It has a default period of 10.
    '''
    # port is the name of generated clk signal, period is the clk period
    if period <= 0:
        raise ValueError("clock period must be greater than zero")
    period_half = period / 2
    #/ initial
    #/ begin
    #/     `port` = 0;
    #/      forever #`period_half`  `port` <= ~`port`;
    #/ end
    pass


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

@ convert 
def Moduledrive_enable(port ='en', start = 2, clk = "clk"):
    '''
    Describes an enable signal drive.
    The enable signal is triggered after `start` positive clock edges.
    '''
    #/ initial begin
    #/ `port` <= 0;
    #/ repeat (`start`) @(posedge `clk`);
    #/ `port` <= 1;
    #/ end
    pass
    
@convert
def Moduledrive_input_signal(ports, files, if_en=False, clk="clk", n_latency=30, if_end=False, end_wait=100, input_file_dir="./sim/Input_Files", **kwargs):
    '''
        Create Excitation for Input ports

        Args:
            ports (list): The list of excitation variable names.
            files (list): The list of excitation variable files.
            if_en (bool, optional): If True, enable signal will be excited. Defaults to False.
            clk (str, optional): Reference clk. Defaults to "clk".
            n_latency (int, optional): Delay before excitation. Defaults to 30.
            if_end (bool, optional): If True, $finish will be added. Defaults to False.
            end_wait (bool, optional): wait x clks before finish. Defaults to 100.
        Modes (parsed with kwargs):
            Mode A1:
                n_cycle (int): The excitation cycle.
            Mode A2:
                n_cycle (int): The excitation cycle.
                n_excites (int): The maximum number of excites.
                grp (str, optional): The excitation group iterable name.
            Mode B:
                n_stamps (list): The list of excitation time stamps.
                grp (str, optional): The excitation group name.
            Mode C:
                n_div_stamps (list): The list of excitation time stamp seperations.
                grp (str, optional): The excitation group name.
    '''
    modes = {
        'A2': ['n_cycle', 'n_excites'],
        'A1': ['n_cycle'],
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
        for port in ports:
            #/ `port` <= Input_`port`;
            pass
        if if_en:
            #/ en <= 1'b1;
            pass
        #/ end
    elif mode == "A2":
        grp = kwargs['grp'] if kwargs['grp'] else "group" # make it optional
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
        for port in ports:
            #/ `port` <= Input_`port`;
            pass
        if if_en:
            #/ en <= 1'b1;
            pass
        #/ end
        #/ end
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
            for port in ports:
                #/ `port` <= Input_`port`;
                pass
            if if_en:
                #/ en <= 1'b1;
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
            for port in ports:
                #/ `port` <= Input_`port`;
                pass
            if if_en:
                #/ en <= 1'b1;
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
    Dump MDA Variables to {output_file_dir}/{name}.txt.

    Arguments:
         name: str - Dump variable name.
         handle: str - Dump variable handle.
         MDAsize: list - Dump MDA size.
         n_latency: int (optional) - The latency before dump. Defaults to 0.
         if_end: bool (optional) - If True, the dump will end with a finish statement. Defaults to False.
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

    # Maybe needs a fix
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
def Moduledump(grp, names, handles, n_latency = 0, if_end = False, end_wait = 40, clk = "clk", en = "en", output_file_dir = "./sim/Output_Files", **kwargs):
    '''
    Dump Variables to a file.
    Args:
        grp (str): The dump variable group name.
        names (list): The list of dump variable names, which is the dumped file name without suffixes.
        handles (list): The list of dump variable handles, which is the content to dump.
        n_latency (int, optional): The latency before dump. Defaults to 0.
        if_end (bool, optional): If True, the dump will end with a finish statement. Defaults to False.
        end_wait (int, optional): How many clks to wait before end. Defaults to 40.
        clk (str, optional): Reference clk. Defaults to "clk".
        en (str, optional): Reference en. Defaults to "en".
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
    for name in names:
        #/ `name`_dat = $fopen("`output_file_dir`/`name`.txt", "w");
        pass
    #/ `grp`_out_indicator = 0;
    
    if n_latency != 0:
        #/ repeat (`L_grp`) @(posedge `clk`);
        pass
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



# binary complement to decimal
def binary_complement_to_decimal(binary_str, is_signed=False):
    binary_str = binary_str.strip()
    if not binary_str:
        return None, "Empty string"

    length = len(binary_str)
    
    if is_signed:
        if binary_str[0] == '1':
            inverted = ''.join('1' if bit == '0' else '0' for bit in binary_str)
            decimal_value = -((int(inverted, 2) + 1) & ((1 << length) - 1))
        else:
            decimal_value = int(binary_str, 2)
    else:
        decimal_value = int(binary_str, 2)

    return decimal_value, "Success"

class Log:
    @staticmethod
    def write_error_info(self, log_dir, error_record):
        '''
        This function should not be modified by user.
        '''
        info = self.display_info()
        # write error info to log file
        log_file = os.path.join(log_dir, "error_info.txt")
        with open(log_file, "a") as f:
            f.write(f"============================Test Case============================\n")
            f.write(info)
            f.write(f"============================Test Case============================\n")
            f.write(f"Recorded Errors:\n" )
            for line in error_record:
                f.write(line)
    
    @staticmethod
    def clear_error_info(self, log_dir):
        '''
        This function should not be modified by user.
        '''
        log_file = os.path.join(log_dir, "error_info.txt")
        with open(log_file, "w") as f:
            f.write("")


class TestcaseGenerator:
    def __init__(self, **kwargs):
        '''
        This class is used to generate test cases for the testbench.
        The parameters are defined in the Parameters class.
        '''
        self.params = kwargs
        
    def generate_testcases(self, Testcase):
        # Get all parameter names and their values
        param_names = list(self.params.keys())
        param_values = list(self.params.values())
        
        # Generate all possible combinations
        testcases = [
            Testcase(**dict(zip(param_names, combination)))
            for combination in itertools.product(*param_values)
        ]
        
        return testcases

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
        
# def main():
#     moduleloader.set_root_dir("./RTL")
#     moduleloader.set_naming_mode("SEQUENTIAL")
#     # moduleloader.saveParams()
#     moduleloader.disEnableWarning()

#     # ModuleFxMatch(QU_IN = QuType(8, 4, True), QU_OUT = QuType(8, -2, True), QU_MODE = QuMode.TRN.TCPL, OF_MODE = OfMode.WRP.TCPL, N_CLK = 0, IF_RST = False)
#     # ModuledumpMDA(name = "pig", handle="very_big_pig", MDAsize=[8, 8, 4,8], n_latency=0, if_end=False, end_wait=40, clk="i_clk", en="en", n_cycle=10, n_dump=10)
#     Moduledrive_input_signal(ports = ["pigs","Very_Big_Pig","Piggies"],files= ["PigInput"], if_en = False, clk = "clk", n_latency = 30, if_end = False, end_wait = 100,input_file_dir="./sim/Input_Files", n_cycle=10, n_excites=10, grp="Piggy")
#     Moduledump(grp="Piggies", names=["pigs","Very_Big_Pig","Piggie"], handles=["pigs","Very_Big_Pig","Piggies_handle"], n_latency = 4, if_end = False, end_wait = 40, clk = "clk", en = "en", output_file_dir = "./sim/Output_Files", n_cycle=10, n_dump=10)
    