import pandas as pd
# import os
# import joblib
# from KeyParam import adder_config_v2, MUL_op, S2U_out, Comp_cfg
import math
import time
import warnings
import numpy as np
# from PyTU import QuMode, OfMode, QuType
# from sklearn.metrics import mean_absolute_error
# from scipy.stats import pearsonr
# from functools import lru_cache
# from PyTU import QuMode, OfMode, QuType
# from EstModule import Est_SUB, Est_ADD, Est_MUL, Est_M2V, Est_Comp

def EstBPADD(DWT):
    db = [9.8, 30.24, 44.5, 66.4, 83.7, 106.7, 121.8, 137.2, 150.1, 168, 182.6, 197.7, 212.5, 227.6, 242.8, 259.8, 275, 289.5, 304, 318.9, 333.5]
    y_pred = 0
    
    if DWT > 20:
        y_pred = 15.2118 * DWT + -0.1101
    else:
        y_pred = db[DWT - 2]
        
    return y_pred

def EstType1_BCB(algo, N, M, width):
    addc = [7.56, 10.92, 17.64, 17.64, 21.00, 30.24, 29.4, 29.4, 34.44, 47.04, 51.8]
    area = 0
    xor = 2.8
    AndGate = 1.12
    OrGate = 1.12
    MUX = 2.8
    AbsAreaLUT = [0, 5, 9.2, 16, 21.6, 26.3]
    if algo == 'MS':
        area += xor * 1 # sign1
        area += xor * 1 # sign2
        
        # abs1, abs2, abs3
        if width > 7:
            absarea = (width-3) * 4.34 + 1.12
            absarea += 2.8 * (width - 1) + 0.84 * (width - 1)
        else:
            absarea = AbsAreaLUT[width - 2]
        area += absarea * 3
        
        # value1 and # value2
        minvalue = 0
        minvalue = (width-1) * 2.8
        if width > 7:
            minvalue += 3 * width * 0.84
        elif width > 2:
            minvalue += width * 0.84
        area += minvalue * 2
        
        # out0 and result
        area += (width * 1.12 + width * 1.12 + 2.8 * (width - 2)) * 2
        area += 0.84 * 2 * width
        
        if width > 2:
            area += EstBPADD(width) * 2 # add1, 4
        
    elif algo == 'SMS':
        if width > 2:
            area += xor * 1 # sign1
            area += xor * 1 # sign2
        
        # abs1, abs2, abs3
        if width > 7:
            absarea = (width-3) * 4.34 + 1.12
            absarea += 2.8 * (width - 1) + 0.84 * (width - 1)
        else:
            absarea = AbsAreaLUT[width - 2]
        area += absarea * 3
        
        # minvalue1 and # minvalue2
        minvalue = 0
        if width > 2:
            minvalue = (width-1) * 2.8
        if width > 7:
            minvalue += 3 * width * 0.84
        elif width > 2:
            minvalue += width * 0.84
        area += minvalue * 2

        # comvalue1 and comvalue2
        if width > 2:
            area += (width-1) * 1.12  * 2
        # area += 0.84 * 2 * width
        
        # out0 and result
        if width > 2:
            area += (width * 1.12 + width * 1.12 + 2.8 * (width - 2)) * 2
            area += 0.84 * 2 * width

        # and
        if width > 2:
            area += EstBPADD(width) * 2 # add1, 4
        if width >= 2 and width <= 12:
            area += addc[width - 2] * 2 # add2, 3
        else:
            area += (addc[-1] + 4.5 * (width - 12)) * 2 # add2, 3
        
        if width == 2:
            area = 4.2
            
    return area

def EstType1_mux1(width, N, M):
    area = 0
    dwt = M * width
    area += dwt * (1.96 + 2.8 + 2.52) + 0.84 * (2 * dwt + 2)
    return area
    
def EstType1_perm(width, N, M):
    area = 1.12 * M * width
    return area

def EstType1_reverse_perm(width, N, M):
    area = 1.12 * M * width
    return area

def EstType1_gen_bcb(width, N, M, algo):
    area = 0
    # print("M:", M)
    for i in range(0, int(M / 2)):
        area += EstType1_BCB(algo, N, M, width)
    # print("GenBCB area:", area)
    return area

def EstType1_counter(N, M, count, value):
    if count == 1:
        area = 5.88 + 1.12
    else:
        area = 5.88 * count + 1.96 * count + 1.12 + (count - 2) * 4.34 + 1.12 
    return area

def EstType1_switch(width, N, M, number, count):
    area = 0
    area += number * width * 5.88
    area += 2 * width * 1.96
    area += (2 * width + 1) * 0.84
    return area

def EstType1_gen_switch(width, N, M, number, count):
    area = 0
    area += EstType1_counter(N=N, M=M, count=count, value=0)
    for i in range(0, int(M / 2), 1):
        area += EstType1_switch(width=width, N=N, M=M, number=number, count=count)
    return area

def EstType1_switch2(width, N, M):
    area = 0
    area += 2 * width * 5.88
    area += (2 * width + 1) * 0.84
    area += 2 * width * 1.96
    return area

def EstType1_gen_switch2(width, N, M):
    area = 0
    area += EstType1_counter(N=N, M=M, count=1, value=0)
    for i in range(0, int(M / 2), 1):
        area += EstType1_switch2(width=width, N=N, M=M)
    return area

def EstType1_early_stop(width, N, M):
    area = 0
    cnt = 0
    # temp
    area += 1.4
    area += 2.8 * N
    # assign early_stop=(flag & temp)?1:0;
    while (N // 4) > 0:
        cnt += (N //4)
        N = N // 4
    area += 1.96 * cnt
    return area

def EstType1_early_stop_memory(width, N, M):
    area = 0
    area += 7.84 * N * width
    area += 1.4 * N * width
    # BUFFER
    area += 1.12 * N * width / 4
    return area

def EstType1_hard_decision(width, N, M):   
    area = 0
    for i in range(0,N):
        area += EstBPADD(width) / 2
    return area

def EstType1_mux2(width, N, M):
    mux_area = 0
    num_switch = int(math.log(int(N / M), 2))
    t = num_switch + 3
    if t & (t - 1) == 0:
        t1 = int(math.log(t, 2))
    else:
        t1 = int(math.log(t, 2)) + 1
    if N==M:
        mux_area += 1.12 * t * M * width + 0.84 * M * width + 0.84
    else:
        mux_area += 1.12 * t * M * width + 1.12 * t + 0.84 * M * width + 1.68
    return mux_area

def EstType1_mux3(width, N, M):
    mux_area = 0
    num_switch = int(math.log(int(N / M), 2))
    t = num_switch + 3
    if t & (t - 1) == 0:
        t1 = int(math.log(t, 2))
    else:
        t1 = int(math.log(t, 2)) + 1
    if N==M:
        mux_area += 3.52 * M * width - 7.555
    else:
        mux_area += 16.422 * t + 5.133 * M * width - 61.13
    return mux_area

def EstType1_delay_reg(width, N, M):
    reg_area = 0
    reg_bit = N * width
    if N == M:
        reg_area += (1.12 + 5.88) * reg_bit
    else:
        reg_area += 5.88 * N * width + 1.12 * M * width
    return reg_area

def EstType1_memory(width, N, M):
    area = 0
    t = int(math.log(N, 2)) - 1
    tm = t * int(N / M)
    if tm & (tm - 1) == 0:
        m = int(math.log(tm, 2))
    else:
        m = int(math.log(tm, 2)) + 1
    reg_bit = tm * M * width
    area += 10.98 * reg_bit + 3.15
    return area  
        
def EstType1_control(width, N, M):
    # only for N = 1024 
    area = 0
    index = math.log2 (N / M)
    if N >= 1024:
        ConArea = [122.079999, 250.599998, 421.119998, 762.719998, 1334.479997, 2517.200001]
        if index < 6:
            area += ConArea[int(index)]
        else:
            area += ConArea[5] * math.pow(1.75, (index - 5))
    elif N ==512:
        ConArea = [120.679998, 240.239998, 397.599998, 739.759998, 1282.679998, 2404.079999]
        if index < 6:
            area += ConArea[int(index)]
        else:
            area += ConArea[5] * math.pow(1.75, (index - 5))
    elif N == 256:
        ConArea = [102.479998, 213.359998, 351.959999, 621.039999, 1114.959997]
        if index < 5:
            area += ConArea[int(index)]
        else:
            area += ConArea[4] * math.pow(1.8, (index - 4))
    elif N == 128:
        ConArea = [103.599999, 184.799999, 314.719998, 572.599998]
        if index < 4:
            area += ConArea[int(index)]
        else:
            area += ConArea[3] * math.pow(1.75, (index - 3))
    elif N == 64:
        ConArea = [93.519999, 163.239999, 293.999998]
        if index < 3:
            area += ConArea[int(index)]
        else:
            area += ConArea[3] * math.pow(1.75, (index - 2))
    elif N == 32:
        ConArea = [80.359999, 150.639999]
        if index < 2:
            area += ConArea[int(index)]
        else:
            area += ConArea[1] * math.pow(1.75, (index - 1))
    else:
        ConArea = [66.079999]
        if index < 1:
            area += ConArea[int(index)]
        else:
            area += ConArea[0] * math.pow(1.75, (index - 0))
    return area

def EstType2_control(width, N, M): 
    area = 0
    # only for N = 1024 
    area = 0
    index = math.log2 (N / M)
    ConArea = [227.920003, 360.640005, 552.440006, 768.880007, 1141.840009, 1778.280009]
    if index < 6:
        area += ConArea[int(index)]
    else:
        area += ConArea[5] * math.pow((index - 5), 1.8)
    return area

def EstType2_BCB(algo, N, M, width):
    area = 0
    addc = [7.56, 10.92, 17.64, 17.64, 21.00, 30.24, 29.4, 29.4, 34.44, 47.04, 51.8]
    xor = 2.8
    AndGate = 1.12
    OrGate = 1.12
    MUX = 2.8
    AbsAreaLUT = [0, 5, 9.2, 16, 21.6, 26.3]
    if algo == 'MS':
        area += xor * 1 # sign1
        area += xor * 1 # sign2
        # abs1, abs2, abs3
        if width > 7:
            absarea = (width-3) * 4.34 + 1.12
            absarea += 2.8 * (width - 1) + 0.84 * (width - 1)
        else:
            absarea = AbsAreaLUT[width - 2]
        area += absarea * 3
        
        # value1 and # value2
        if 7 >= width > 2:
            minvalue = (width-1) * 2.8
        elif width > 7:
            minvalue += 3 * width * 0.84
        else:  
            minvalue += width * 0.84
        area += minvalue * 2
        
        # out0 and result
        if width > 2:
            area += (width * 1.12 + width * 1.12 + 2.8 * (width - 2)) * 2
            area += 0.84 * 2 * width
        
        if width > 2:
            area += EstBPADD(width)
            area += EstBPADD(width)
    if algo == 'SMS':
        area += xor * 1 # sign1
        area += xor * 1 # sign2
        
        # abs1, abs2, abs3
        if width > 7:
            absarea = (width-3) * 4.34 + 1.12
            absarea += 2.8 * (width - 1) + 0.84 * (width - 1)
        else:
            absarea = AbsAreaLUT[width - 2]
        area += absarea * 3
        
        # minvalue1 and # minvalue2
        minvalue = (width-1) * 2.8
        if width > 7:
            minvalue += 3 * width * 0.84
        else:  
            minvalue += width * 0.84
        area += minvalue * 2

        # comvalue1 and comvalue2
        area += (width-1) * 1.12  * 2
        # area += 0.84 * 2 * width
        
        # out0 and result
        area += (width * 1.12 + width * 1.12 + 2.8 * (width - 2)) * 2
        area += 0.84 * 2 * width

        # and
        area += EstBPADD(width) * 2 # add1, 4
        area += addc[width - 2] * 2 # add2, 3
    return area

def EstType2_pipe_reg(width, N, M):
    area = 0
    area += 5.58 * M * width
    return area

def EstType2_perm(width, N, M):
    area = 1.12 * M * width
    return area

def EstType2_reverse_perm(width, N, M):
    area = 1.12 * M * width
    return area
    
def EstType2_gen_bcb(width, N, M, algo):
    area = 0
    for i in range(0, int(M / 2)):
        area += EstType2_BCB(width=width, algo=algo, N=N, M=M)
    return area

def EstType2_switch(width, N, M, number, count):
    t = int(math.log(number, 2))
    count = t
    area = 0
    area += number * width * 5.88
    area += 2 * width * 1.96
    area += (2 * width + 1) * 0.84
    return area

def EstType2_switch2(width, N, M):
    area = 0
    area += 2 * width * 5.88
    area += (2 * width + 1) * 0.84
    area += 2 * width * 1.96
    return area

def EstType2_counter(N, M, count, value):
    if count == 1:
        area = 5.88 + 1.12
    else:
        area = 5.88 * count + 1.96 * count + 1.12 + (count - 2) * 4.34 + 1.12 
    return area

def EstType2_gen_switch(width, N, M, number):
    t = int(math.log(number, 2))
    count = t
    area = 0
    value = 0
    area += EstType2_counter(N=N, M=M, count=count, value=value)
    for i in range(0, int(M / 2), 1):
        area += EstType2_switch(width=width,N=N,M=M,number=number,count=count)
        pass
    return area

def EstType2_gen_switch2(width, N, M, count):
    value = 0
    area = 0
    area += EstType2_counter(N=N, M=M, count=count, value=value)
    for i in range(0, int(M / 2), 1):
        area += EstType2_switch2(width=width,N=N,M=M)
    return area

def EstType2_xor_pass(width, N, M):
    area = 0
    area += (2.8 + 1.12) * (N // 2)
    return area

def EstType2_shuffle(width, N, M):
    area = 0
    area += 1.12 * N
    return area

def EstType2_hard_decision(width, N, M):   
    area = 0
    for i in range(0,N):
        area += EstBPADD(width) / 2
        # print("EstType2_hard_decision BPADD:", EstBPADD(width))
    return area

def EstType2_delay_reg(width, N, M):
    reg_area = 0
    reg_bit = N * width
    if N == M:
        reg_area += (1.12 + 5.88) * reg_bit
    else:
        reg_area += 5.88 * N * width + 1.12 * M * width
    return reg_area

def EstType2_G_matrix(width, N, M):
    area = 0
    n = int(math.log(N, 2))
    area += EstType2_hard_decision(width=width, N=N, M=M)
    # print("EstType2_hard_decision:", EstType2_hard_decision(width=width, N=N, M=M))
    area += EstType2_hard_decision(width=width, N=N, M=M)
    # print("EstType2_hard_decision:", EstType2_hard_decision(width=width, N=N, M=M))
    area += EstType2_xor_pass(width=width, N=N, M=M,)
    # print("EstType2_xor_pass:", EstType2_xor_pass(width=width, N=N, M=M))
    for i in range(1, n):
        area += EstType2_shuffle(width=width, N=N, M=M)
        # print("EstType2_shuffle:", EstType2_shuffle(width=width, N=N, M=M))
        area += EstType2_xor_pass(width=width, N=N, M=M)
        # print("EstType2_xor_pass:", EstType2_xor_pass(width=width, N=N, M=M))
    # if N <= 1024:
    inc = 2.8 * N
    while (N // 4) > 0:
        N = N // 4
        inc += 1.96 * N
    inc += 1.12
    # else:  
    #     inc = 7.7 * N
    # print("inc:", inc)
    area += inc
    return area

def EstType2_mux1(width, N, M):
    mux_area = 0
    mux_bit = 2 * M * width
    mux_area += 2.94 * mux_bit + 5.54
    return mux_area

def EstType2_mux2(width, N, M):
    mux_area = 0
    num_switch = int(math.log(int(N / M), 2))
    t3 = int(math.log(N, 2)) - 1
    if num_switch < t3:
        t = num_switch + 2
    else:
        t = num_switch
    if t & (t - 1) == 0:
        t1 = int(math.log(t, 2))
    else:
        t1 = int(math.log(t, 2)) + 1
    if N==M:
        mux_area += 1.12 * t * M * width + 0.84 * M * width + 0.84
    else:
        mux_area += 1.12 * t * M * width + 1.12 * t + 0.84 * M * width + 1.68
    return mux_area

def EstType2_mux3(width, N, M):
    mux_area = 0
    t3 = int(math.log(N, 2)) - 1
    num_switch = int(math.log(int(N / M), 2))
    if num_switch < t3:
        t = num_switch + 2
    else:
        t = num_switch
    if t & (t - 1) == 0:
        t1 = int(math.log(t, 2))
    else:
        t1 = int(math.log(t, 2)) + 1
    if N==M:
        mux_area += 3.08 * M * width
    elif num_switch == 1:
        mux_area += 3.08 * M * width + 1.12 * int((M * width)/3) + 3.92
    elif t & (t - 1) == 0:
        mux_area += 1.96 * (t/2) * M * width + 1.68 * M * width +  + 8.12
    elif t >= t3:
        param = min(abs(t - (2 ** t1)), abs(t - (2 ** (t1 - 1))))
        mux_area += 2.8 * param * M * width + 1.96 * M * width + 2.24 + 1.12 * (t - t3) + 1.4 * (t1 + 3 * (t - t3)) + 0.84
    else:
        mux_area += 1.2977 * t * M * width - 3.94
    return mux_area
        
def EstType2_memory(width, N, M):
    area = 0
    t = int(math.log(N, 2))
    m = int(math.log(t * int(N / M), 2))
    t1 = t * int(N/M)
    reg_bit = t1 * M * width
    if N==M:
        area += (7 + 2.8) * reg_bit + 0.84 * 2 * M * width + 2.8 * 2 * (2 ** m-1) * M * width + t1 * (1.12 + 1.4 + 1.96)
    elif t >= 5:
        area += 12.94479776 * reg_bit - 2.22096911 * M * width + 738.8406822538236
    else:
        area += 9.8 * reg_bit + 2.8 * 2 * (2 ** m-1) * M * width + t * 1.4 + 0.84 * M * width * (m-1)
    return area   
     
def Esttop(archi, algo, N, M, width):
    area = 0
    cnt = 0
    if archi == 'TypeI':
        t1 = int(math.log(N, 2)) - 1
        tm = t1 * int(N / M)
        if tm & (tm - 1) == 0:
            m = int(math.log(tm, 2))
        else:
            m = int(math.log(tm, 2)) + 1
        num_switch = int(math.log(int(N / M), 2))
        t = num_switch + 3
        if t & (t - 1) == 0:
            t2 = int(math.log(t, 2))
        else:
            t2 = int(math.log(t, 2)) + 1
            
        mux1 = EstType1_mux1(width=width, N=N, M=M)         
        # print("EstType1_mux1 area:", EstType1_mux1(width=width, N=N, M=M))
        
        genbcb = EstType1_gen_bcb(width=width, N=N, M=M, algo=algo)
        # print("EstType1_gen_bcb area:", EstType1_gen_bcb(width=width, N=N, M=M, algo=algo))
        
        mux2 = EstType1_mux2(width=width, N=N, M=M)
        # print("EstType1_mux2 area:", EstType1_mux2(width=width, N=N, M=M))
        
        perm = EstType1_perm(width=width, N=N, M=M)
        # print("EstType1_perm area:", EstType1_perm(width=width, N=N, M=M))
        
        rperm = EstType1_reverse_perm(width=width, N=N, M=M)
        # print("EstType1_reverse_perm area:", EstType1_reverse_perm(width=width, N=N, M=M))
        
        switch = 0
        switch2 = 0
        if N > M:
            for i in range(0, num_switch - 1):
                temp1 = int(math.pow(2, num_switch - i))
                temp2 = int(math.log(temp1, 2))
                switch += EstType1_gen_switch(width=width, M=M, N=N, number=temp1, count=temp2) 
                # print("EstType1_gen_switch area:", EstType1_gen_switch(width=width, M=M, N=N, number=temp1, count=temp2))
                
            switch2 = EstType1_gen_switch2(width=width, M=M, N=N)
            # print("EstType1_gen_switch2 area:", EstType1_gen_switch2(width=width, M=M, N=N))
            
        mux3 = EstType1_mux3(width=width, N=N, M=M)
        # print("EstType1_mux3 area:", EstType1_mux3(width=width, N=N, M=M))
        
        delay_reg = EstType1_delay_reg(width=width, N=N, M=M)
        # print("EstType1_delay_reg area:", EstType1_delay_reg(width=width, N=N, M=M))
        
        memory = EstType1_memory(width=width, N=N, M=M)
        # print("EstType1_memory area:", EstType1_memory(width=width, N=N, M=M))
        
        control = EstType1_control(width=width, N=N, M=M)
        # print("EstType1_control area:", EstType1_control(width=width, N=N, M=M))
        
        early_stop = EstType1_early_stop(width=width, N=N, M=M)
        # print("EstType1_early_stop area:", EstType1_early_stop(width=width, N=N, M=M))
        
        early_stop_memory = EstType1_early_stop_memory(width=width, N=N, M=M) * 0.3
        # print("EstType1_early_stop_memory area:", EstType1_early_stop_memory(width=width, N=N, M=M)* 0.3)
        
        hard_decision = EstType1_hard_decision(width=width, N=N, M=M)
        # print("EstType1_hard_decision area:", EstType1_hard_decision(width=width, N=N, M=M))
        
        if width <= 2 and algo == "SMS":
            area = mux1 / 3 + genbcb / 6 + mux2 / 2 + perm / 2 + rperm / 2 + switch + switch2 + mux3 + delay_reg + memory / 2 + control + early_stop + early_stop_memory + hard_decision
        else:
            area = mux1 + genbcb + mux2 + perm + rperm + switch + switch2 + mux3 + delay_reg + memory + control + early_stop + early_stop_memory + hard_decision
        
    if archi == 'TypeII':
        t1 = int(math.log(N, 2)) - 10
        m = int(math.log((t1 + 1) * int(N / M), 2))
        num_switch = int(math.log(int(N / M), 2))
        if num_switch < t1:
            t = num_switch + 2
        else:
            t = num_switch
        count = t
        # if t & (t - 1) == 0:
        #     t2 = int(math.log(t, 2))
        # else:
        #     t2 = int(math.log(t, 2)) + 1

        area += EstType2_mux1(width=width, N=N, M=M)
        cnt += 1
        print("EstType2_mux1 area:", EstType2_mux1(width=width, N=N, M=M))
        
        area += EstType2_gen_bcb(width=width, N=N, M=M, algo=algo)
        cnt += 1
        print("EstType2_gen_bcb area:", EstType2_gen_bcb(width=width, N=N, M=M, algo=algo))
        
        area += EstType2_mux2(width=width, N=N, M=M)
        cnt += 1
        print("EstType2_mux2 area:", EstType2_mux2(width=width, N=N, M=M))

        if N > M:
            for i in range(0, num_switch - 1):
                temp1 = int(math.pow(2, num_switch - i))
                temp2 = int(math.log(temp1, 2))
                area += EstType2_gen_switch(width=width, M=M, N=temp1, number=temp2)
                cnt += 1
                print("EstType2_gen_switch area:", EstType2_gen_switch(width=width, M=M, N=temp1, number=temp2))
                
            area += EstType2_gen_switch2(width=width, M=M, N=N, count=count)
            cnt += 1
            print("EstType2_gen_switch2 area:", EstType2_gen_switch2(width=width, M=M, N=N, count=count))
    
        if num_switch < t1:
            area += EstType2_perm(width=width, N=N, M=M)
            cnt += 1
            print("EstType2_perm area:", EstType2_perm(width=width, N=N, M=M))
            
            area += EstType2_reverse_perm(width=width, N=N, M=M)
            cnt += 1
            print("EstType2_reverse_perm area:", EstType2_reverse_perm(width=width, N=N, M=M))

        area += EstType2_mux3(width=width, N=N, M=M)
        cnt += 1
        print("EstType2_mux3 area:", EstType2_mux3(width=width, N=N, M=M))
        
        area += EstType2_delay_reg(width=width, N=N, M=M)
        cnt += 1
        print("EstType2_delay_reg area:", EstType2_delay_reg(width=width, N=N, M=M))
        
        area += EstType2_mux1(width=width, N=N, M=M)
        cnt += 1
        print("EstType2_mux1 area:", EstType2_mux1(width=width, N=N, M=M))
        
        area += EstType2_gen_bcb(width=width, N=N, M=M, algo=algo)
        cnt += 1
        print("EstType2_gen_bcb area:", EstType2_gen_bcb(width=width, N=N, M=M, algo=algo))
        
        area += EstType2_mux2(width=width, N=N, M=M)
        cnt += 1
        print("EstType2_mux2 area:", EstType2_mux2(width=width, N=N, M=M))

        if N > M:
            for i in range(0, num_switch - 1):
                temp1 = int(math.pow(2, num_switch - i))
                temp2 = int(math.log(temp1, 2))
                area += EstType2_gen_switch(width=width, M=M, N=temp1, number=temp2)
                cnt += 1
                print("EstType2_gen_switch area:", EstType2_gen_switch(width=width, M=M, N=temp1, number=temp2))
                
            area += EstType2_gen_switch2(width=width, M=M, N=N, count=count)
            cnt += 1
            print("EstType2_gen_switch2 area:", EstType2_gen_switch2(width=width, M=M, N=N, count=count))
    
        if num_switch < t1:
            area += EstType2_perm(width=width, N=N, M=M)
            cnt += 1
            print("EstType2_perm area:", EstType2_perm(width=width, N=N, M=M))
            
            area += EstType2_reverse_perm(width=width, N=N, M=M)
            cnt += 1
            print("EstType2_reverse_perm area:", EstType2_reverse_perm(width=width, N=N, M=M))

        area += EstType2_mux3(width=width, N=N, M=M)
        cnt += 1
        print("EstType2_mux3 area:", EstType2_mux3(width=width, N=N, M=M))
        
        area += EstType2_delay_reg(width=width, N=N, M=M)
        cnt += 1
        print("EstType2_delay_reg area:", EstType2_delay_reg(width=width, N=N, M=M))
        
        area += EstType2_memory(width=width, N=N, M=M)
        cnt += 1
        print("EstType2_memory area:", EstType2_memory(width=width, N=N, M=M))
        
        area += EstType2_pipe_reg(width=width, N=N, M=M)
        cnt += 1
        print("EstType2_pipe_reg area:", EstType2_pipe_reg(width=width, N=N, M=M))
        
        area += EstType2_pipe_reg(width=width, N=N, M=M)
        cnt += 1
        print("EstType2_pipe_reg area:", EstType2_pipe_reg(width=width, N=N, M=M))
        
        area += EstType2_control(width=width, N=N, M=M)
        cnt += 1
        print("EstType2_control area:", EstType2_control(width=width, N=N, M=M))
        
        area += EstType2_G_matrix(width=width, N=N, M=M)  
        cnt += 1  
        print("EstType2_G_matrix area:", EstType2_G_matrix(width=width, N=N, M=M))    
        
        print("Total number of components:", cnt)
    
    area = float(area)
    return area    

def CalcTP(period:float, N:int, M:int, iter:float):
    # period in ns
    # N: code length
    # M: parallelism
    # iter: average iteration count
    # Return TP in Gbps
    # Latency = N * math.log2(N) * iter / M + 2
    Latency = (2*(math.log2(N)-1) * iter + 1) * N / M + 2 # Type I
    # Latency = 18 * iter + 3
    K = N / 2 # Information Bits
    return K / period / Latency

def EstBPDecoder_GUI(ConfigFileName="./config.json"):
    # Load Configuration
    import json
    
    try:
        with open(ConfigFileName, 'r') as f:
            config = json.load(f)
        
        archi = config.get("Hardware Architecture", "TypeI")
        algo = config.get("Decoding Algorithm", "MS")
        N = config.get("Code Length", 1024)
        M = config.get("Parallelism", 1024)
        width = config.get("Data Width", 5)
        
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
    
    start_gen_time = time.perf_counter()
    area = Esttop(archi=archi, algo=algo, N=N, M=M, width=width)
    TP = CalcTP(period=50, N=N, M=M, iter=5.63)
    end_gen_time = time.perf_counter()
    print(f"Generated {archi} {algo} decoder with Code Length N={N} and Parallelism M={M} in {end_gen_time - start_gen_time} seconds.\n")
    return area, TP

if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    # Example usagear
    start_time = time.time()
    area, throughput = EstBPDecoder_GUI(ConfigFileName="./config.json")
    # area = Esttop(archi = "TypeI", algo = "SMS", N = 1024, M = 1024, width = 4)
    end_time = time.time()
    execution_time = end_time - start_time
    print("Execution time:", execution_time)
    print(f"area: {area:.2f} um^2")
    print(f"throughput: {throughput:.5f} Gbps")