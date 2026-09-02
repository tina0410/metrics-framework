import pandas as pd
import numpy as np
# import os
import joblib
from EstModule import Est_SUB, Est_ADD, Est_MUL, Est_M2V
import math
import time
import warnings
# import numpy as np
from PyTU import QuMode, OfMode, QuType

def EstLS(Model_ADD, ModelMUL, ModelSU_out, SU_in_db, N_T:int, N_R:int, P_T:int, P_R:int, QU_Y:QuType, QU_P:QuType, QU_H:QuType, QU_M_V:QuType, N_PIPELINES:list=[1, 1]):
  pred = 0
  STG_T = math.ceil(N_T / P_T)
  # M2V
  pred += Est_M2V(Model_ADD, ModelMUL, ModelSU_out, SU_in_db, M = P_R, V = P_T, QU_M=QU_Y, QU_V=QU_P, QU_M_V=QU_M_V, QU_OUT=QU_H, N_PIPELINES=N_PIPELINES)
  # print("M2V Area: ", pred)
  if STG_T > 1:
    # ADD
    AddArea = Est_ADD(Model_ADD, QU_H.DWT, QU_H.FRAC, QU_H.IF_SIGNED, QU_H.DWT, QU_H.FRAC, QU_H.IF_SIGNED, QU_H.DWT + 1, QU_H.FRAC, 0) * P_R
    # print("ADD Area: ", AddArea)
    # mux
    MuxArea= P_R * QU_H.DWT * 2.52
    # print("MUX Area: ", MuxArea)
    # reg
    RegArea = P_R * QU_H.DWT * 7.84
    # print("REG Area: ", RegArea)
    pred += AddArea + MuxArea + RegArea
  
  pred_values = np.asarray(pred).reshape(-1)
  if pred_values.size != 1:
    raise ValueError(f"LSCE area model must return one value, got shape {np.asarray(pred).shape}")
  pred = float(pred_values[0])
  return pred

def CalcTP(period:float, N_T:int, N_R:int, P_T:int, P_R:int, QU_H:QuType):
    # Period in ns
    # Return TP in k Channel / second
    STG_T = math.ceil(N_T / P_T)
    return 1e6 / STG_T / period / N_R

def EstLSCE_GUI(ModelADD, ModelMUL, ModelSU_out, SU_in_db, ConfigFileName="./config.json"):
    # Load Configuration
    snr = 15
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
    
    area = EstLS(ModelADD, ModelMUL, ModelSU_out, SU_in_db, N_T=N_T, N_R=N_R, P_T=P_T, P_R=P_R, QU_Y=QU_Y, QU_P=QU_P, QU_H=QU_H, QU_M_V=QU_M_V, N_PIPELINES=N_PIPELINES)
    nmse = -10*math.log10(snr) - 10*math.log10(N_T)
    TP = CalcTP(period=50, N_T=N_T, N_R=N_R, P_T=P_T, P_R=P_R, QU_H=QU_H)
    return area, nmse, TP

if __name__ == '__main__':
  # os.chdir(os.path.dirname(__file__))
  warnings.filterwarnings("ignore")
  path = "."
  SU_in_db = pd.read_excel(path + '/model/SU_in.xlsx', sheet_name='SU_in', header = 0)
  Sub_db = pd.read_excel(path + '/model/SU_in.xlsx', sheet_name='Sub', header = 0)
  ModelADD = joblib.load(path +'/model/ADD_area.pkl')
  ModelMUL = joblib.load(path +'/model/pure_MUL_area.pkl')
  ModelSU_out = joblib.load(path +'/model/SU_out_FxP_area.pkl')
  su_in_db_id = "ctx_su_in_db"
  model_su_out_id = "ctx_model_su_out"
  
  start = time.time()
  area, nmse, throughput =EstLSCE_GUI(ModelADD, ModelMUL, ModelSU_out, SU_in_db, ConfigFileName="./config.json")
  end = time.time()
  
  print(f"Area: {area:.2f} um^2, NMSE: {nmse:.2f} dB, Throughput: {throughput:.5f} kChannels/s")
  print(f"Time taken: {(end - start)*1000:.2f} ms")