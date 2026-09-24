###################################################################################################
# Module Name: FxMatch
# Description: This module is used to match the input data to the output data with different data width and fractional bits.
# Author: Changhan Li
# Author: Bolin Li
# Revised：Yifang Dai
# Date: 2024.12.4
# Revised Date:2025.3.24 
# Version: V0.2.1
# Doc Version: V0.1.0
# Dependency Modules: 
#     - Delay (V0.1.0)
# Release Notes: 
#     - V0.2.1: Fixed bugs in all round modes and checked results in all round modes.
###################################################################################################
import pytv
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname, abspath

sys.path.append(dirname(dirname(__file__)))
sys.path.append(dirname(__file__))
from Delay import ModuleDelay
from PyTU import QuMode, OfMode, QuType

@convert
def ModuleFxMatch(QU_IN: QuType, QU_OUT: QuType, QU_MODE: QuMode.TRN | QuMode.RND, OF_MODE: OfMode.WRP | OfMode.SAT, N_CLK: int, IF_RST_N: bool):
    """
    Docstring for ModuleFxMatch
    
    :param QU_IN: QuType(9,3,True)
    :type QU_IN: QuType
    :param QU_OUT: QuType(9,3,True)
    :type QU_OUT: QuType
    :param QU_MODE: QuMode.TRN.TCPL
    :type QU_MODE: QuMode
    :param OF_MODE: OfMode.WRP.TCPL
    :type OF_MODE: OfMode
    :param N_CLK: 4
    :type N_CLK: int
    :param IF_RST_N: True
    :type IF_RST_N: bool
    """
    # ============================================================
    # Decode QU_MODE and OF_MODE from PyTV symbolic parameters
    # to stable Enum values that can be reliably compared
    # ============================================================
    
    # Decode QU_MODE
    qu_mode_str = str(QU_MODE)
    qu_type = type(QU_MODE).__name__
    if qu_type == 'TRN':
        if 'TCPL' in qu_mode_str:
            QU_MODE_E = QuMode.TRN.TCPL
        elif 'SMGN' in qu_mode_str:
            QU_MODE_E = QuMode.TRN.SMGN
        else:
            raise ValueError(f"Unknown QU_MODE in TRN: {qu_mode_str}, full: {QU_MODE}")
    elif qu_type == 'RND':
        if 'POS_INF' in qu_mode_str:
            QU_MODE_E = QuMode.RND.POS_INF
        elif 'NEG_INF' in qu_mode_str:
            QU_MODE_E = QuMode.RND.NEG_INF
        elif 'ZERO' in qu_mode_str:
            QU_MODE_E = QuMode.RND.ZERO
        elif 'INF' in qu_mode_str:
            QU_MODE_E = QuMode.RND.INF
        elif 'CONV' in qu_mode_str:
            QU_MODE_E = QuMode.RND.CONV
        else:
            raise ValueError(f"Unknown QU_MODE in RND: {qu_mode_str}, full: {QU_MODE}")
    else:
        raise ValueError(f"Unknown QU_MODE type: {qu_type}, full: {QU_MODE}")
    
    # Decode OF_MODE
    of_mode_str = str(OF_MODE)
    of_type = type(OF_MODE).__name__
    if of_type == 'WRP':
        if 'TCPL' in of_mode_str:
            OF_MODE_E = OfMode.WRP.TCPL
        else:
            raise ValueError(f"Unknown OF_MODE in WRP: {of_mode_str}, full: {OF_MODE}")
    elif of_type == 'SAT':
        if 'TCPL' in of_mode_str:
            OF_MODE_E = OfMode.SAT.TCPL
        elif 'SMGN' in of_mode_str:
            OF_MODE_E = OfMode.SAT.SMGN
        elif 'ZERO' in of_mode_str:
            OF_MODE_E = OfMode.SAT.ZERO
        else:
            raise ValueError(f"Unknown OF_MODE in SAT: {of_mode_str}, full: {OF_MODE}")
    else:
        raise ValueError(f"Unknown OF_MODE type: {of_type}, full: {OF_MODE}")
    
    # ============================================================
    # End of decoding - all subsequent logic uses QU_MODE_E / OF_MODE_E
    # ============================================================
    
    # Parsing the input arguments
    # the IF_RST_N_LIST should not be passed to the submodules
    if N_CLK > 0:
        # Expand the boolean to a list of the same value
        IF_RST_N_LIST = [IF_RST_N] * N_CLK
    elif N_CLK == 0:
        IF_RST_N_LIST = [False] # No sequential logic. This is only for type alignment
    else: # N_CLK < 0
        raise ValueError("N_CLK must be non-negative.")
        
    #/ `timescale 1ns / 1ps
    #/ module FxMatch(
    #/     i_data, o_data
    if N_CLK > 0:
        #/ , i_clk
        if any(IF_RST_N_LIST):
            #/ , i_rst_n
            pass
    #/ );
    #/ input  wire [`QU_IN.DWT`-1:0]  i_data; // Input data
    #/ output wire [`QU_OUT.DWT`-1:0] o_data; // Output data
    if N_CLK > 0:
        #/ input wire i_clk; // Clock
        if any(IF_RST_N_LIST):
            #/ input wire i_rst_n; // Reset, negative effective
            pass
    #/ //
    # For simplicity, unsigned input is expanded with a 0 sign bit, and for unsigned output, the sign bit is truncated.
    EQ_QU_IN = QuType(8, 0, True)
    if QU_IN.IF_SIGNED == False:
        EQ_QU_IN.DWT = QU_IN.DWT + 1
        EQ_QU_IN.FRAC = QU_IN.FRAC
        EQ_QU_IN.IF_SIGNED = True
        #/ wire [`EQ_QU_IN.DWT`-1:0] i_data_eq;
        #/ assign i_data_eq = {1'b0, i_data};
    else:
        EQ_QU_IN = QU_IN
        #/ wire [`EQ_QU_IN.DWT`-1:0] i_data_eq;
        #/ assign i_data_eq = i_data;
    EQ_QU_OUT = QuType(8, 0, True)
    if QU_OUT.IF_SIGNED == False:
        EQ_QU_OUT.DWT = QU_OUT.DWT + 1
        EQ_QU_OUT.FRAC = QU_OUT.FRAC
        EQ_QU_OUT.IF_SIGNED = True  # EQ_QU_OUT is signed after processing
    else:
        EQ_QU_OUT = QU_OUT
    # Rule out the case where only one stage is needed
    #/ wire [`EQ_QU_OUT.DWT`-1:0] o_data_eq;
    if EQ_QU_OUT.LSB() > EQ_QU_IN.MSB():
        # Quantization Stage only
        #/ // Quantization Stage
        if EQ_QU_OUT.LSB() - EQ_QU_IN.MSB() > 1:
            # Impossible to round up
            if QU_MODE_E == QuMode.TRN.TCPL:
                #/ assign o_data_eq = i_data_eq[`EQ_QU_IN.DWT`-1] ? {`EQ_QU_OUT.DWT`{1'b1}} : {`EQ_QU_OUT.DWT`{1'b0}};
                pass
            else:  # All other modes
                #/ assign o_data_eq = {`EQ_QU_OUT.DWT`{1'b0}};
                pass
        else: # EQ_QU_OUT.LSB() - EQ_QU_IN.MSB() == 1
            # Possible to round up
            if QU_MODE_E == QuMode.TRN.TCPL:   
                #/ assign o_data_eq = i_data_eq[`EQ_QU_IN.DWT`-1] ? {`EQ_QU_OUT.DWT`{1'b1}} : {`EQ_QU_OUT.DWT`{1'b0}};
                pass
            elif QU_MODE_E == QuMode.RND.INF or QU_MODE_E == QuMode.RND.NEG_INF:
                #/ assign o_data_eq = (i_data_eq == {1'b1, {`EQ_QU_IN.DWT-1`{1'b0}}}) ? {`EQ_QU_OUT.DWT`{1'b1}} : {`EQ_QU_OUT.DWT`{1'b0}};
                pass
            else:  # TRN.SMGN, RND.POS_INF, RND.ZERO, RND.CONV
                #/ assign o_data_eq = {`EQ_QU_OUT.DWT`{1'b0}};
                pass
            
    elif EQ_QU_OUT.MSB() < EQ_QU_IN.LSB():
        # Overflow Stage only
        #/ // Overflow Stage
        if OF_MODE_E == OfMode.WRP.TCPL or OF_MODE_E == OfMode.SAT.ZERO:
            #/ assign o_data_eq = {`EQ_QU_OUT.DWT`{1'b0}};
            pass
        elif OF_MODE_E == OfMode.SAT.TCPL:
            #/ assign o_data_eq = i_data_eq[`EQ_QU_IN.DWT`-1]
            #/ ? {1'b1, {`EQ_QU_OUT.DWT-1`{1'b0}}}
            #/ : {
            #/ (i_data_eq == {`EQ_QU_IN.DWT`{1'b0}})
            #/ ? {`EQ_QU_OUT.DWT`{1'b0}}
            #/ : {1'b0, {`EQ_QU_OUT.DWT-1`{1'b1}}}
            #/ };
            pass
        elif OF_MODE_E == OfMode.SAT.SMGN:
            if EQ_QU_OUT.DWT > 2:
                #/ assign o_data_eq = i_data_eq[`EQ_QU_IN.DWT`-1]
                #/ ? {1'b1, {`EQ_QU_OUT.DWT-2`{1'b0}}, 1'b1}
                #/ : {
                #/ (i_data_eq == {`EQ_QU_IN.DWT`{1'b0}})
                #/ ? {`EQ_QU_OUT.DWT`{1'b0}}
                #/ : {1'b0, {`EQ_QU_OUT.DWT-1`{1'b1}}}
                #/ };
                pass
            elif EQ_QU_OUT.DWT == 2:
                #/ assign o_data_eq = i_data_eq[`EQ_QU_IN.DWT`-1]
                #/ ? {1'b1, 1'b1}
                #/ : {
                #/ (i_data_eq == {`EQ_QU_IN.DWT`{1'b0}})
                #/ ? {`EQ_QU_OUT.DWT`{1'b0}}
                #/ : {1'b0, {`EQ_QU_OUT.DWT-1`{1'b1}}}
                #/ };
                pass
            else:
                #/ assign o_data_eq = 1'b0;
                pass
        else:
            raise ValueError(f"Unmatched OF_MODE in Overflow protection 1: {OF_MODE}, type: {type(OF_MODE)}, name: {type(OF_MODE).__name__}")
    else:
        # Both Quantization and Overflow Stages
        #/ // Quantization Stage
        QU_QUAN = QuType(DWT = 8, FRAC= 0, IF_SIGNED = True)
        if EQ_QU_OUT.LSB() > EQ_QU_IN.LSB():
            # // Truncate / Round precision
            if QU_MODE_E == QuMode.TRN.TCPL:
                QU_QUAN.set(MSB = EQ_QU_IN.MSB(), LSB = EQ_QU_OUT.LSB())
                #/ wire [`QU_QUAN.DWT`-1:0] op_quan; // Quantization output
                #/ assign op_quan = i_data_eq[`EQ_QU_IN.DWT`-1:`EQ_QU_IN.DWT - QU_QUAN.DWT`];
                pass
            elif QU_MODE_E == QuMode.TRN.SMGN:
                QU_QUAN.set(MSB = EQ_QU_IN.MSB(), LSB = EQ_QU_OUT.LSB())
                #/ wire [`QU_QUAN.DWT`-1:0]  op_quan; // Quantization output
                #/ wire [`EQ_QU_IN.DWT`-1:0] i_data_eq_abs;
                #/ wire [`QU_QUAN.DWT`-1:0]  op_quan_abs;
                #/ assign i_data_eq_abs = i_data_eq[`EQ_QU_IN.DWT`-1] ? ~i_data_eq + 1'b1 : i_data_eq;
                #/ assign op_quan_abs   = i_data_eq_abs[`EQ_QU_IN.DWT`-1:`EQ_QU_IN.DWT - QU_QUAN.DWT`];
                #/ assign op_quan       = i_data_eq[`EQ_QU_IN.DWT`-1] ? ~op_quan_abs + 1'b1 : op_quan_abs;
            elif QU_MODE_E == QuMode.RND.POS_INF:
                QU_QUAN.set(MSB = EQ_QU_IN.MSB()+1 , LSB = EQ_QU_OUT.LSB())
                #/ wire [`QU_QUAN.DWT`-1:0] op_quan; // Quantization output
                #/ wire [`EQ_QU_IN.DWT`:0]  i_data_eq_fill;
                #/ assign i_data_eq_fill = {i_data_eq[`EQ_QU_IN.DWT`-1] , i_data_eq};
                comp_val = f"{EQ_QU_IN.DWT - QU_QUAN.DWT+1}'b1" + "0" * (EQ_QU_IN.DWT - QU_QUAN.DWT)
                #/ assign op_quan = (i_data_eq_fill[`EQ_QU_IN.DWT - QU_QUAN.DWT`:0] >= `comp_val`)
                #/ ? (i_data_eq_fill[`EQ_QU_IN.DWT`:`EQ_QU_IN.DWT - QU_QUAN.DWT+1`] + 1'b1)
                #/ : i_data_eq_fill[`EQ_QU_IN.DWT`:`EQ_QU_IN.DWT - QU_QUAN.DWT+1`];
            elif QU_MODE_E == QuMode.RND.NEG_INF:
                QU_QUAN.set(MSB = EQ_QU_IN.MSB()+1 , LSB = EQ_QU_OUT.LSB())
                #/ wire [`QU_QUAN.DWT`-1:0] op_quan; // Quantization output
                #/ wire [`EQ_QU_IN.DWT`:0]  i_data_eq_fill;
                #/ assign i_data_eq_fill = {i_data_eq[`EQ_QU_IN.DWT`-1] , i_data_eq};
                comp_val = f"{EQ_QU_IN.DWT - QU_QUAN.DWT+1}'b1" + "0" * (EQ_QU_IN.DWT - QU_QUAN.DWT)
                #/ assign op_quan = (i_data_eq_fill[`EQ_QU_IN.DWT - QU_QUAN.DWT`:0] > `comp_val`)
                #/ ? (i_data_eq_fill[`EQ_QU_IN.DWT`:`EQ_QU_IN.DWT - QU_QUAN.DWT+1`] + 1'b1)
                #/ : i_data_eq_fill[`EQ_QU_IN.DWT`:`EQ_QU_IN.DWT - QU_QUAN.DWT+1`];
            elif QU_MODE_E == QuMode.RND.ZERO:
                QU_QUAN.set(MSB = EQ_QU_IN.MSB()+1 , LSB = EQ_QU_OUT.LSB())
                #/ wire [`QU_QUAN.DWT`-1:0] op_quan; // Quantization output
                #/ wire [`EQ_QU_IN.DWT`:0]  i_data_eq_fill;
                #/ assign i_data_eq_fill = {i_data_eq[`EQ_QU_IN.DWT`-1] , i_data_eq};
                comp_val = f"{EQ_QU_IN.DWT - QU_QUAN.DWT+1}'b1" + "0" * (EQ_QU_IN.DWT - QU_QUAN.DWT)
                #/ assign op_quan = (i_data_eq_fill[`EQ_QU_IN.DWT - QU_QUAN.DWT`:0] > `comp_val`)
                #/ ? (i_data_eq_fill[`EQ_QU_IN.DWT`:`EQ_QU_IN.DWT - QU_QUAN.DWT+1`] + 1'b1)
                #/ : (
                #/     ((i_data_eq_fill[`EQ_QU_IN.DWT - QU_QUAN.DWT`:0] == `comp_val`) && (i_data_eq_fill[`EQ_QU_IN.DWT`-1]))
                #/     ? (i_data_eq_fill[`EQ_QU_IN.DWT`:`EQ_QU_IN.DWT - QU_QUAN.DWT+1`] + 1'b1)
                #/     : i_data_eq_fill[`EQ_QU_IN.DWT`:`EQ_QU_IN.DWT - QU_QUAN.DWT+1`]
                #/ );
                pass
            elif QU_MODE_E == QuMode.RND.INF:
                QU_QUAN.set(MSB = EQ_QU_IN.MSB()+1, LSB = EQ_QU_OUT.LSB())
                #/ wire [`QU_QUAN.DWT`-1:0] op_quan; // Quantization output
                #/ wire [`EQ_QU_IN.DWT`:0]  i_data_eq_fill;
                #/ assign i_data_eq_fill = {i_data_eq[`EQ_QU_IN.DWT`-1] , i_data_eq};
                comp_val = f"{EQ_QU_IN.DWT - QU_QUAN.DWT+1}'b1" + "0" * (EQ_QU_IN.DWT - QU_QUAN.DWT)
                #/ assign op_quan = (i_data_eq_fill[`EQ_QU_IN.DWT - QU_QUAN.DWT`:0] > `comp_val`)
                #/ ? (i_data_eq_fill[`EQ_QU_IN.DWT`:`EQ_QU_IN.DWT - QU_QUAN.DWT+1`] + 1'b1)
                #/ : (
                #/     ((i_data_eq_fill[`EQ_QU_IN.DWT - QU_QUAN.DWT`:0] == `comp_val`) && (~i_data_eq_fill[`EQ_QU_IN.DWT`-1]))
                #/     ? (i_data_eq_fill[`EQ_QU_IN.DWT`:`EQ_QU_IN.DWT - QU_QUAN.DWT+1`] + 1'b1)
                #/     : i_data_eq_fill[`EQ_QU_IN.DWT`:`EQ_QU_IN.DWT - QU_QUAN.DWT+1`]
                #/ );
            elif QU_MODE_E == QuMode.RND.CONV:
                QU_QUAN.set(MSB = EQ_QU_IN.MSB()+1 , LSB = EQ_QU_OUT.LSB())
                #/ wire [`QU_QUAN.DWT`-1:0] op_quan; // Quantization output
                #/ wire [`EQ_QU_IN.DWT`:0]  i_data_eq_fill;
                #/ assign i_data_eq_fill = {i_data_eq[`EQ_QU_IN.DWT`-1] , i_data_eq};
                comp_val = f"{EQ_QU_IN.DWT - QU_QUAN.DWT+1}'b1" + "0" * (EQ_QU_IN.DWT - QU_QUAN.DWT)
                #/ assign op_quan = (i_data_eq_fill[`EQ_QU_IN.DWT - QU_QUAN.DWT`:0] > `comp_val`)
                #/ ? (i_data_eq_fill[`EQ_QU_IN.DWT`:`EQ_QU_IN.DWT - QU_QUAN.DWT+1`] + 1'b1)
                #/ : (
                #/     ((i_data_eq_fill[`EQ_QU_IN.DWT - QU_QUAN.DWT`:0] == `comp_val`) && (i_data_eq_fill[`EQ_QU_IN.DWT - QU_QUAN.DWT+1`]))
                #/     ? (i_data_eq_fill[`EQ_QU_IN.DWT`:`EQ_QU_IN.DWT - QU_QUAN.DWT+1`] + 1'b1)
                #/     : i_data_eq_fill[`EQ_QU_IN.DWT`:`EQ_QU_IN.DWT - QU_QUAN.DWT+1`]
                #/ );
                pass
            else:
                raise ValueError(f"Unmatched QU_MODE in Rounding/Truncation: {QU_MODE}, type: {type(QU_MODE)}, name: {type(QU_MODE).__name__}")
        elif EQ_QU_OUT.LSB() == EQ_QU_IN.LSB():
            #/ // Perfect LSB match
            QU_QUAN.set(MSB=EQ_QU_IN.MSB, LSB=EQ_QU_OUT.LSB)
            #/ wire [`QU_QUAN.DWT`-1:0] op_quan; // Quantization output
            #/ assign op_quan = i_data_eq;
            pass
        else: # EQ_QU_OUT.LSB() < EQ_QU_IN.LSB()
            #/ // Pad extra LSB bits with 0
            QU_QUAN.set(MSB=EQ_QU_IN.MSB, LSB = EQ_QU_OUT.LSB)
            #/ wire [`QU_QUAN.DWT`-1:0] op_quan; // Quantization output
            #/ assign op_quan = {i_data_eq, {`QU_QUAN.DWT - EQ_QU_IN.DWT`{1'b0}}};
            pass
            
            
        #/ // Overflow Stage
        if EQ_QU_OUT.MSB() < QU_QUAN.MSB():
            #/ // Overflow protection
            if OF_MODE_E == OfMode.WRP.TCPL:
                #/ assign o_data_eq = op_quan[`EQ_QU_OUT.DWT`-1:0];
                pass
            elif OF_MODE_E == OfMode.SAT.TCPL:
                neg_max = f"{EQ_QU_OUT.DWT}'b1" + "0" * (EQ_QU_OUT.DWT - 1)
                pos_max = f"{EQ_QU_OUT.DWT}'b0" + "1" * (EQ_QU_OUT.DWT - 1)
                #/ assign o_data_eq = (op_quan[`QU_QUAN.DWT`-1:`EQ_QU_OUT.DWT`] != {`QU_QUAN.DWT - EQ_QU_OUT.DWT`{op_quan[`EQ_QU_OUT.DWT`-1]}})
                #/ ? (op_quan[`QU_QUAN.DWT`-1] ? `neg_max` : `pos_max`)
                #/ : op_quan[`EQ_QU_OUT.DWT`-1:0];
                pass
            elif OF_MODE_E == OfMode.SAT.SMGN:
                if EQ_QU_OUT.DWT > 1:
                    neg_max = f"{EQ_QU_OUT.DWT}'b1" + "0" * (EQ_QU_OUT.DWT - 2) + "1"
                    pos_max = f"{EQ_QU_OUT.DWT}'b0" + "1" * (EQ_QU_OUT.DWT - 1)
                    #/ assign o_data_eq = (op_quan[`QU_QUAN.DWT`-1:`EQ_QU_OUT.DWT`] != {`QU_QUAN.DWT - EQ_QU_OUT.DWT`{op_quan[`EQ_QU_OUT.DWT`-1]}})
                    #/ ? (op_quan[`QU_QUAN.DWT`-1] ? `neg_max` : `pos_max`)
                    #/ : (op_quan[`EQ_QU_OUT.DWT`-1:0] == {1'b1 , {`EQ_QU_OUT.DWT-1`'b0}}) ? op_quan[`EQ_QU_OUT.DWT`-1:0] +1'b1 : op_quan[`EQ_QU_OUT.DWT`-1:0];
                    pass
                else:
                    neg_pos_max = f"{EQ_QU_OUT.DWT}'b0"
                    #/ assign o_data_eq = `neg_pos_max`;
                    pass
                pass
            elif OF_MODE_E == OfMode.SAT.ZERO:
                #/ assign o_data_eq = (op_quan[`QU_QUAN.DWT`-1:`EQ_QU_OUT.DWT`] != {`QU_QUAN.DWT - EQ_QU_OUT.DWT`{op_quan[`EQ_QU_OUT.DWT`-1]}})
                #/ ? `EQ_QU_OUT.DWT`'b0
                #/ : op_quan[`EQ_QU_OUT.DWT`-1:0];
                pass
            else:
                raise ValueError(f"Unmatched OF_MODE in Overflow protection 2: {OF_MODE}, type: {type(OF_MODE)}, name: {type(OF_MODE).__name__}")
        elif EQ_QU_OUT.MSB() == QU_QUAN.MSB():
            #/ // Perfect MSB match
            if OF_MODE_E == OfMode.SAT.SMGN:
                if EQ_QU_OUT.DWT >1:
                    #/ assign o_data_eq = (op_quan == {1'b1 , {`QU_QUAN.DWT-1`'b0}}) ? op_quan + 1'b1 : op_quan;
                    pass
                else:
                    #/ assign o_data_eq = 1'b0;
                    pass
            else:  # WRP.TCPL, SAT.TCPL, SAT.ZERO
                #/ assign o_data_eq = op_quan;
                pass
            
        else: # EQ_QU_OUT.MSB() > QU_QUAN.MSB()
            #/ // Pad extra MSB bits with sign bit
            if QU_MODE_E == QuMode.TRN.TCPL or QU_MODE_E == QuMode.TRN.SMGN:
                #/ assign o_data_eq = {{`EQ_QU_OUT.DWT - QU_QUAN.DWT`{op_quan[`QU_QUAN.DWT`-1]}}, op_quan};
                pass
            else:  # All rounding modes
                #/ assign o_data_eq = op_quan[`QU_QUAN.DWT`-1] ? {{`EQ_QU_OUT.DWT - QU_QUAN.DWT`{i_data_eq[`EQ_QU_IN.DWT`-1]}}, op_quan} : {{`EQ_QU_OUT.DWT - QU_QUAN.DWT`{op_quan[`QU_QUAN.DWT`-1]}}, op_quan};
                pass
            

    # Truncate the sign bit for unsigned output
    #/ wire [`QU_OUT.DWT`-1:0] o_data_trunc;
    if QU_OUT.IF_SIGNED == False:
        #/ // Truncate the sign bit for unsigned output
        #/ assign o_data_trunc = o_data_eq[`EQ_QU_OUT.DWT`-2:0];
        pass
    else:
        #/ assign o_data_trunc = o_data_eq;
        pass

    # Delay the output data
    inst_ports = {
        "i_data": "o_data_trunc",
        "o_data": "o_data"
    }
    if N_CLK > 0:
        inst_ports["i_clk"] = "i_clk"
        if any(IF_RST_N_LIST):
            inst_ports["i_rst_n"] = "i_rst_n"
    ModuleDelay(DWT = QU_OUT.DWT, N_CLK = N_CLK, IF_RST_N = IF_RST_N, PORTS = inst_ports) # type: ignore

    #/ endmodule
    pass
