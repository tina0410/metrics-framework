###################################################################################################
# Module Name: LSCE
# Description: This module performs matrix and vector multiplication.
# Author: Changhan Li
# Date: 2025.07.16
# Version: V0.1.0
# Doc Version: V0.1.0
# Dependency Modules:
#     - AdderTree (V0.1.0)
#     - Mul (V0.2.1) 
#     - Add (V0.2.1)
#     - PyTU (V0.0.2)
#     - FxMatch (V0.2.1)
#     - Delay (V0.1.0)
#     - M2V (V0.1.0)
# Release Notes: 
#     - V0.1.0: Initial Draft
###################################################################################################

import pytv
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname, abspath

sys.path.append(dirname(dirname(__file__)))
sys.path.append(dirname(__file__))
from PyTU import QuMode, OfMode, QuType

import math

from Add import ModuleAdd
from M2V import ModuleM2V

@convert
def ModuleLSCE(N_T:int, N_R:int, P_T:int, P_R:int, QU_Y:QuType, QU_P:QuType, QU_H:QuType, QU_M_V:QuType, QU_MODE:QuMode, OF_MODE:OfMode, N_PIPELINES:list=[1, 1]):
    # Input Argument Parsing #
    STG_T = math.ceil(N_T / P_T)
    # End of Input Argument Parsing #
    #/  module LSCE (
    #/      i_Y, i_P, o_H, i_clk
    if STG_T > 1:
        #/  , i_ctrl_stg
        pass
    #/  );
    #/  input wire [`P_R*P_T`*`QU_Y.DWT`-1:0] i_Y; // col-major order
    #/  input wire [`P_T`*`QU_P.DWT`-1:0] i_P;
    #/  output wire [`P_R`*`QU_H.DWT`-1:0] o_H;
    #/  input wire i_clk;
    if STG_T > 1:
        #/  input wire [1:0] i_ctrl_stg;
        pass
    
    # M2V Module Instantiation
    # Matrix Size: P_R x P_T
    # Vector Size: P_T x 1
    #/  wire [`P_R`*`QU_H.DWT`-1:0] H_temp;
    inst_ports = {
        "i_matrix": "i_Y",
        "i_vector": "i_P",
        "o_result": "H_temp",
        "i_clk": "i_clk"
    }
    ModuleM2V(M=P_R, V=P_T, QU_M=QU_Y, QU_V=QU_P, QU_M_V=QU_M_V, QU_OUT=QU_H, QU_MODE=QU_MODE, OF_MODE=OF_MODE, TYPE="REAL", N_PIPELINES=N_PIPELINES, PORTS=inst_ports)
    if STG_T <= 1:
        # Skip Accumulation
        #/  assign o_H = H_temp;
        pass
    else:
        # Accumulation Block
        # Vector Size: P_R x 1
        #/  wire [`P_R`*`QU_H.DWT`-1:0] H_add_result;
        #/  reg [`P_R`*`QU_H.DWT`-1:0] H_accum;
        for i in range(P_R):
            inst_ports = {
                "i_data_1": f"H_temp[{i+1}*{QU_H.DWT}-1:{i}*{QU_H.DWT}]",
                "i_data_2": f"H_accum[{i+1}*{QU_H.DWT}-1:{i}*{QU_H.DWT}]",
                "o_data": f"H_add_result[{i+1}*{QU_H.DWT}-1:{i}*{QU_H.DWT}]"
            }
            ModuleAdd(QU_IN_1=QU_H, QU_IN_2=QU_H, QU_OUT=QU_H, N_PIPELINES=0, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=False, PORTS=inst_ports)
            #/  always @(posedge i_clk) begin
            #/      if (i_ctrl_stg == 2'b00) begin
            #/          H_accum[`i+1`*`QU_H.DWT`-1:`i`*`QU_H.DWT`] <= `QU_H.DWT`'b0;
            #/      end 
            #/      else if (i_ctrl_stg == 2'b01) begin
            #/          H_accum[`i+1`*`QU_H.DWT`-1:`i`*`QU_H.DWT`] <= H_temp[`i+1`*`QU_H.DWT`-1:`i`*`QU_H.DWT`];
            #/      end 
            #/      else if (i_ctrl_stg == 2'b10) begin
            #/          H_accum[`i+1`*`QU_H.DWT`-1:`i`*`QU_H.DWT`] <= H_add_result[`i+1`*`QU_H.DWT`-1:`i`*`QU_H.DWT`];
            #/      end
            #/      else begin
            #/          H_accum[`i+1`*`QU_H.DWT`-1:`i`*`QU_H.DWT`] <= H_accum[`i+1`*`QU_H.DWT`-1:`i`*`QU_H.DWT`];
            #/      end
            #/  end
            pass
        #/  assign o_H = H_accum;
        pass
    
    #/  endmodule 

def GenLSCE(ConfigFileName="./config.json", GenRoot="./RTL", *, config=None):
    # Load Configuration
    import json
    
    try:
        if config is None:
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
    
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file {ConfigFileName}: {e}")
        return
    
    except Exception as e:
        print(f"Error loading config: {e}")
        return
    
    # Generate Module
    moduleloader.reset()
    moduleloader.set_language_mode("VERILOG")
    moduleloader.set_root_dir(GenRoot)
    moduleloader.set_naming_mode("SEQUENTIAL")
    # moduleloader.saveParams()
    moduleloader.disEnableWarning()
    import time
    start_gen_time = time.perf_counter()
    ModuleLSCE(N_T=N_T, N_R=N_R, P_T=P_T, P_R=P_R, QU_Y=QU_Y, QU_P=QU_P, QU_H=QU_H, QU_M_V=QU_M_V, QU_MODE=QU_MODE, OF_MODE=OF_MODE, N_PIPELINES=N_PIPELINES)
    end_gen_time = time.perf_counter()
    print(f"ModuleLSCE generated in {end_gen_time - start_gen_time:.5f} seconds")
    return end_gen_time - start_gen_time

if __name__ == "__main__":
    time = GenLSCE(ConfigFileName="./config.json", GenRoot="./RTL")
    # moduleloader.set_root_dir("./RTL")
    # moduleloader.set_naming_mode("SEQUENTIAL")
    # # moduleloader.saveParams()
    # moduleloader.disEnableWarning()
    # # Test the ModuleLSCE function
    # N_T = 256
    # N_R = 16
    # P_T = 16
    # P_R = 4
    # QU_Y = QuType(16, 0, True)
    # QU_P = QuType(16, 0, True)
    # QU_H = QuType(16, 0, True)
    # QU_M_V = QuType(16, 0, True)
    # QU_MODE = QuMode.TRN.TCPL
    # OF_MODE = OfMode.WRP.TCPL
    # N_PIPELINES = [1, 1]
    # ModuleLSCE(N_T=N_T, N_R=N_R, P_T=P_T, P_R=P_R, QU_Y=QU_Y, QU_P=QU_P, QU_H=QU_H, QU_M_V=QU_M_V, QU_MODE=QU_MODE, OF_MODE=OF_MODE, N_PIPELINES=N_PIPELINES)
