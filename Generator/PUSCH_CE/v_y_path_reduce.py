from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

import os, sys
from os.path import dirname

sys.path.append(dirname(__file__))
from basic_modules import QuType

@convert
def ModuleY_PATH_REDUCE(Qu_Data: QuType, INPUT_INDEX_LIST: list[int], OUTPUT_INDEX_LIST: list[int], HAS_VALID_READY: bool) -> None:
    '''
    Docstring for ModuleY_PATH_REDUCE
    A Banyan Network module (Static Routing) that performs path reduction for Y symbols.
    It maps specific logical inputs (defined in INPUT_INDEX_LIST) to specific ordered outputs 
    (defined in OUTPUT_INDEX_LIST).
    
    The module checks if every element in OUTPUT_INDEX_LIST is contained in INPUT_INDEX_LIST.
    It effectively acts as a wire crossbar/selector to reduce or reorder the input bus.

    Mapping Logic:
    For each index 'k' in OUTPUT_INDEX_LIST, the module finds the corresponding physical 
    index 'j' in INPUT_INDEX_LIST such that INPUT_INDEX_LIST[j] == OUTPUT_INDEX_LIST[k], 
    and assigns Output[k] = Input[j].

    Valid/Ready Handshake:
    If HAS_VALID_READY is True, a single valid input and a single ready output are generated.
    The valid signal indicates all input data is valid. The ready signal is directly tied to 1
    (combinational passthrough, always ready). Downstream can use valid to gate consumption.

    :param Qu_Data: QuType(10, 8, True)
    Quantization type of the data payload. Defines the bit width of the input/output ports.
    :type Qu_Data: QuType
    :param INPUT_INDEX_LIST: list(range(12))
    List of logical IDs present at the input ports (in order of physical ports 0 to N-1).
    :type INPUT_INDEX_LIST: list[int]
    :param OUTPUT_INDEX_LIST: [1, 0, 6, 7, 2, 3, 8, 9]
    List of logical IDs required at the output ports (in order of physical ports 0 to M-1).
    Must be a subset of INPUT_INDEX_LIST.
    :type OUTPUT_INDEX_LIST: list[int]
    :param HAS_VALID_READY: False
    If True, generates a single valid input and a single ready output for handshake.
    :type HAS_VALID_READY: bool
    '''
    
    # Input validation
    # Check if OUTPUT_INDEX_LIST is a subset of INPUT_INDEX_LIST
    input_set = set(INPUT_INDEX_LIST)
    for out_idx in OUTPUT_INDEX_LIST:
        if out_idx not in input_set:
            raise ValueError(f"Output index {out_idx} is not present in INPUT_INDEX_LIST {INPUT_INDEX_LIST}.")

    # Determine port counts
    num_inputs = len(INPUT_INDEX_LIST)
    num_outputs = len(OUTPUT_INDEX_LIST)
    
    # Bit width extraction
    dwt = Qu_Data.DWT

    #/ `timescale 1ns / 1ps
    #/ module Y_PATH_REDUCE (
    
    # Generate Input Ports
    for i in range(num_inputs):
        name_data = f"data_in_{i}"
        #/ input [`dwt`-1:0] `name_data`,
        pass

    # Single valid/ready handshake
    if HAS_VALID_READY:
        #/ input  valid_in,
        #/ output ready_in,
        #/ input  ready_out,
        #/ output valid_out,
        pass

    # Generate Output Ports
    for i in range(num_outputs):
        name_data = f"data_out_{i}"
        comma = ',' if i < num_outputs - 1 else ''
        #/ output [`dwt`-1:0] `name_data``comma`
        pass

    #/ );

    # Valid/Ready: combinational passthrough, always ready
    if HAS_VALID_READY:
        #/ assign ready_in  = ready_out;
        #/ assign valid_out = valid_in;
        pass

    # Logic Implementation
    # We map the physical input port index to the physical output port index
    # based on the logical ID matching.
    
    for i in range(num_outputs):
        logical_id = OUTPUT_INDEX_LIST[i]
        
        # Find which physical input port 'j' has this logical_id
        physical_input_idx = INPUT_INDEX_LIST.index(logical_id)
        
        in_data_name = f"data_in_{physical_input_idx}"
        out_data_name = f"data_out_{i}"
        
        #/ assign `out_data_name` = `in_data_name`;
        pass

    #/ endmodule

if __name__ == "__main__":
    # Test case to verify parameter passing
    q_type = QuType(16, 8, True)
    in_list = [0, 1, 2, 3, 4, 5]
    out_list = [0, 2, 5]
    ModuleY_PATH_REDUCE(q_type, in_list, out_list, True)
