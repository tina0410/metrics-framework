# coding = utf-8
# Date: 2025.3.12
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

import itertools
import PyTU
try:
    import pyverilog
    from pyverilog.vparser.parser import parse
except ImportError:  # Port parsing is not needed by the MUL simulation flow.
    pyverilog = None
    parse = None
import os
import shutil
from datetime import datetime

# define colors
BLUE = "\033[1;34m"
RED = "\033[1;33m"
RESET = "\033[0m"


# Declare the required ports
@ convert 
def ModuleDecl(input_ports, output_ports):

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
    

# generate input_rdy signal and output_rdy signal
# output rdy is set to 1 after input rdy is set to 1 and latency later
@ convert
def Moduledrive_rdy(port_in= "Input_rdy", port_out = "Output_rdy", port_en= "en" ,clk_period = 10, clk = "clk", start=1, latency = 4, N_excitations = 100):
    '''
    Describes Input/Output Ready Drive.
    
    Loop `N_excitations` times after `port_en` enable signal is switched ON. The freqency of ready signals is equivilent to clock signals.  
    '''

    # drive input_rdy signal
    half_period = clk_period / 2
    wait_end = 30

    #/ integer `port_in`_iter;
    #/ initial begin
    #/ `port_in` <= 0;
    if port_en is not None:
        #/ repeat (1) @(posedge `port_en`);
        pass

    #/ `port_in` <= 1;
    #/ for (`port_in`_iter=0; `port_in`_iter<`N_excitations`; `port_in`_iter=`port_in`_iter+1) begin
    #/     # (`half_period`) `port_in` <= ~ `port_in`;
    #/ end
    #/ end

    #/ integer `port_out`_iter;
    #/ initial begin
    #/ `port_out` <= 0;
    if port_en is not None:
        #/ repeat(1) @(posedge `port_en`);
        pass
    #/ repeat (`latency`) @(posedge `clk`); // wait for `latency` cycles
    #/ `port_out` <= 1;
    #/ for (`port_out`_iter=0; `port_out`_iter<`N_excitations`; `port_out`_iter=`port_out`_iter+1) begin
    #/     # (`half_period`) `port_out` <= ~ `port_out`;
    #/ end
    #/ repeat(`wait_end`) @(posedge `clk`);
    #/ $finish;
    #/ end

    pass 

@ convert
def Moduledrive_input(port, file_name, wait_cycles, fistream_port ,input_rdy_port = "Input_rdy", output_rdy_port = "Output_rdy", clk = "clk"):
    '''
   Reads input data from a file specified by `file_name` and feeds it into the port one line at a time. 

   It waits for the system to be ready (indicated by `input_rdy_port`) before transferring each piece of data. 
   The module reads binary values from the file and provides them to `port`. It continues this process until the end of the file is reached.
    '''
    file_handle = port + "_dat"
    file_read_handle = port + "_st"
    file_name = "\"" + file_name + "\""
    #/ integer `file_handle`, `file_read_handle`;
    #/ initial begin
    #/ repeat (`wait_cycles`) @(posedge `clk`);
    #/ `file_handle` = $fopen(`file_name`, "r");
    #/ while (!$feof(`file_handle`)) begin
    #/     `file_read_handle` = $fscanf(`file_handle`, "%b\\n", `fistream_port`);
    #/      repeat(1) @(posedge `input_rdy_port`);
    #/     `port` <= `fistream_port`;
    #/ end
    #/ $fclose(`file_handle`);
    #/ end
    pass


@ convert
def Moduledump_output(port, file_name, wait_cycles, fostream_port, output_rdy_port = "Output_rdy", clk = "clk", N_excitations = 9):
    '''
    Dump output signal specified in `port` to a file specified by `file_name` on posedge of `output_rdy_port`. The process will loop `N_excitations` times.
    '''
    file_handle = port + "_dat"
    iter = port + "_iter"
    file_name = "\"" + file_name + "\""
    #/ integer `file_handle`;
    #/ integer `iter`;
    #/ initial begin
    #/ repeat (`wait_cycles`) @(posedge `clk`);
    #/ `file_handle` = $fopen(`file_name`, "w");
    #/ for (`iter`=0; `iter`<`N_excitations`; `iter`=`iter`+1) begin
    #/     repeat(1) @(posedge `output_rdy_port`);
    #/     repeat(1) @(negedge `clk`);
    #/     $fdisplay(`file_handle`, "%b", `port`);
    #/ end
    #/ $fclose(`file_handle`);
    #/ end
    pass

#FxMatch.ModuleFxMatch(QU_IN = QU_IN, QU_OUT = QU_OUT, N_CLK = N_CLK, IF_RST_N = IF_RST_N, QU_MODE=QU_MODE, OF_MODE=OF_MODE)


"""
What do we need to decide the behavior of the testbench?
0. Basic Signals: clk, rst
1. Input data timing (start, period)
2. Output data timing (start, period)
3. Input data file directory
4. Output data file directory
"""
class myPort:
    def __init__(self, name, width, direction):
        self.name = name
        self.width = width
        self.direction = direction
        self.type = type


def judge_port_type(decl):
    port_type = None
    port_direction = None
    port_name  = None
    port_width = None
    list_in_decl = decl.list
    for item in list_in_decl:
        port_name = item.name
        if item.width is not None:
            port_width = int(item.width.msb.value) - int(item.width.lsb.value) + 1
        if isinstance(item, pyverilog.vparser.ast.Input):
            port_direction = "INPUT"
        if isinstance(item, pyverilog.vparser.ast.Output):
            port_direction = "OUTPUT"
        if isinstance(item, pyverilog.vparser.ast.Wire):
            port_type = "WIRE"
        if isinstance(item, pyverilog.vparser.ast.Reg):
            port_type = "REG"
    return port_name, port_direction, port_type, port_width


def parse_verilog_port(verilog_file):
    module_name = None
    ports_info = []
    ast, directives = parse([verilog_file])
    module = ast.description.definitions[0]
    ports = module.portlist.ports

    # gather module ports information
    for port in ports:
        myport = myPort(port.name, port.width, port.type)
        ports_info.append(myport)

    # deal with non-ansi ports
    decl_type = pyverilog.vparser.ast.Decl
    for i_port, port in enumerate(ports_info):
        if port.direction is None or port.width is None:
            # find the corresponding declaration
            for i_decl, decl in enumerate(module.items):
                if isinstance(decl, decl_type):
                    port_name, port_direction, port_type, port_width = judge_port_type(decl)
                    if port_name == port.name:
                        if port_direction is not None:
                            port.direction = port_direction
                        if port_type is not None:
                            port.type = port_type
                        if port_width is not None:
                            port.width = port_width
                        break

                      
    # print ports information
    module_name = module.name
    # for port in ports_info:
    #     print(f"Port name: {port.name}, Port direction: {port.direction}, Port type: {port.type}, Port width: {port.width}")
    return module_name, ports_info

@ convert
def ModuleMyTb(verilog_code, configures):
    input_ports = configures["input_ports"]
    output_ports = configures["output_ports"]
    module_name = configures["module_name"]
    
    #/ module MyTb;
    #/ // Ports declaration
    ModuleDecl(input_ports = input_ports, output_ports = output_ports, OUTMODE = "PRINT")
    #/ endmodule
    pass



class TestbenchGenerator:
    def __init__ (self, loader, dut_path = None, tb_path = None):
        self.moduleloader = loader
        self.verilog_code = str()
        self.dut_path = str()  # path to the device under test
        self.tb_path = str()
        self.configures = dict()
        if dut_path is not None:
            self.set_dut_path(dut_path)
        if tb_path is not None:
            self.set_tb_path(tb_path)

    def set_dut_path(self, dut_path):
        self.dut_path = dut_path

    def set_tb_path(self, tb_path):
        self.tb_path = tb_path

    def get_verilog_code(self):
        if self.dut_path is None:
            raise ValueError(f"Path to DUT is not specified.")
        # if self.dut_path does not exist:
        if not os.path.exists(self.dut_path):
            raise ValueError(f"Path to DUT {self.dut_path} does not exist.")
        with open(self.dut_path, "r", encoding="utf-8") as f:
            self.verilog_code = f.read()

    def add_port_info(self, ports_info):
        self.configures["input_ports"] = []
        self.configures["output_ports"] = []
        for port in ports_info:
            if port.direction == "INPUT":
                self.configures["input_ports"].append(port)
            if port.direction == "OUTPUT":
                self.configures["output_ports"].append(port)

    def add_module_name_info(self, module_name):
        self.configures["module_name"] = module_name


    def genrate_testbench(self,dut_path=None, tb_path=None):
        self.get_verilog_code()
        # if tb path is not None, check whether it exists
        # if tb_path is None, new a directory named "TBGEN" in the same directory as DUT
        if tb_path is not None:
            if not os.path.exists(tb_path):
                raise ValueError(f"Specified path to TB {tb_path} does not exist.")
        else:
            tb_path = os.path.join(os.path.dirname(self.dut_path), "TBGEN")
            if not os.path.exists(tb_path):
                os.mkdir(tb_path)
        self.set_tb_path(tb_path)
        moduleloader.set_root_dir(tb_path)
        moduleloader.set_naming_mode("SEQUENTIAL")
        module_name, ports_info = parse_verilog_port(self.dut_path)
        self.add_port_info(ports_info)
        self.add_module_name_info(module_name)
        # generate testbench code
        ModuleMyTb(verilog_code = self.dut_path, configures = self.configures)

def calc_qublas_dwt(QU_VAR):
    dwt = QU_VAR.DWT
    dwt_frac = QU_VAR.FRAC
    if (QU_VAR.IF_SIGNED):
        dwt_int_frac = dwt - 1
    else:
        dwt_int_frac = dwt
    dwt_int = dwt_int_frac - dwt_frac
    return dwt_int, dwt_frac


def int_to_hex_with_length(num):
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
    source_file_path = os.path.join(source_dir, old_filename)
    target_file_path = os.path.join(target_dir, new_filename)
    try:
        shutil.move(source_file_path, target_file_path)
        print(f"Moving {old_filename} to {target_dir} and renaming it as {new_filename}")
    except FileNotFoundError:
        print(f"File {old_filename} not found in {source_dir}")
    except Exception as e:
        print(f"Error in Moving {old_filename} to {target_dir} and renaming it as {new_filename} : {e}")


def get_current_time_as_string():
    current_time = datetime.now()
    time_string = current_time.strftime("%Y-%m-%d %H:%M:%S")  
    return time_string


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
    
    def write_error_info(Testcase, log_dir, error_record):
        '''
        This function should not be modified by user.
        '''
        info = Testcase.display_info()
        # write error info to log file
        log_file = os.path.join(log_dir, "error_info.txt")
        with open(log_file, "a") as f:
            f.write(f"============================Test Case============================\n")
            f.write(info)
            f.write(f"============================Test Case============================\n")
            f.write(f"Recorded Errors:\n" )
            for line in error_record:
                f.write(line)
    
    def clear_error_info(Testcase, log_dir):
        '''
        This function should not be modified by user.
        '''
        log_file = os.path.join(log_dir, "error_info.txt")
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

