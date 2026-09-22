import os

def add_arrays(arr1, arr2):
    result = []
    for i in range(len(arr1)):
        result.append(arr1[i] + arr2[i])
    return result
# ---------------------------------------------------- ADD ----------------------------------------------------
def adder_config_v2(dwt_in1, frac_in1, sign_in1, dwt_in2, frac_in2, sign_in2, dwt_out, frac_out, n_pipelines):
    LSB_OUT = -frac_out
    MSB_OUT = dwt_out - frac_out - 1
    LSB_IN1 = -frac_in1
    MSB_IN1 = dwt_in1 - frac_in1 - 1
    LSB_IN2 = -frac_in2
    MSB_IN2 = dwt_in2 - frac_in2 - 1
    min_LSB_in = min(LSB_IN1, LSB_IN2)
    max_LSB_in = max(LSB_IN1, LSB_IN2)
    min_MSB_in = min(MSB_IN1, MSB_IN2) 
    max_MSB_in = max(MSB_IN1, MSB_IN2) + 1

    sign_out = sign_in1 or sign_in2

    cfg_m = [] # [gnd,dir,xor,carry,add_carry] of a + b
    for i in range(min_LSB_in, max_MSB_in + 1):
        gnd_bit = 0
        dir_conn_bit = 0
        xor_bit = 0
        carry_bit = 0
        add_carry_bit = 0

        if sign_out == 1:
            if i < min_LSB_in:
                gnd_bit = 1
            if i < max_LSB_in and i >= min_LSB_in:
                dir_conn_bit = 1
            if i <= max_MSB_in and i >= max_LSB_in:
                xor_bit = 1
            if i < max_MSB_in and i >= max_LSB_in:
                carry_bit = 1
            if i <= max_MSB_in and i > max_LSB_in:
                add_carry_bit = 1
        else:
            if (i > MSB_IN1 or i < LSB_IN1) and (i < LSB_IN2 or i > MSB_IN2):
                gnd_bit = 1
            if i == max_MSB_in:
                if max_MSB_in - 1 >= max_LSB_in and max_MSB_in - 1 < max_MSB_in and min_MSB_in >= max_LSB_in:
                    gnd_bit = 0
                else:
                    gnd_bit = 1
            if i <= MSB_IN1 and i <= MSB_IN2 and i >= LSB_IN1 and i >= LSB_IN2:
                xor_bit = 1
            if i >= max_LSB_in and i < max_MSB_in and min_MSB_in >= max_LSB_in:
                carry_bit = 1
            if i > max_LSB_in and i < max_MSB_in and min_MSB_in >= max_LSB_in:
                add_carry_bit = 1
            if add_carry_bit != 1 and ((MSB_IN1 >= i >= LSB_IN1 and (i < LSB_IN2 or i > MSB_IN2)) or (MSB_IN2 >= i >= LSB_IN2 and (i < LSB_IN1 or i > MSB_IN1))):
                dir_conn_bit = 1

        cfg_m.append([gnd_bit, dir_conn_bit, xor_bit, carry_bit, add_carry_bit])
    # print(cfg_m)

    cfg_r =[0,0,0,0,0] # [gnd,dir,xor,carry,add_carry] of result
    cfg_m_fix = []
    for i in range(len(cfg_m)):
        cfg_m_fix.append([0,0,0,0,0])

    for i in range(LSB_OUT, MSB_OUT + 1):
        if i < min_LSB_in:
            cfg_r[0] += 1
        elif max_MSB_in >= i >= min_LSB_in:
            cfg_r = add_arrays(cfg_m[i-min_LSB_in], cfg_r)
            cfg_m_fix[i-min_LSB_in] = cfg_m[i-min_LSB_in]
        if sign_out == 0:
            if i > max_MSB_in:
                cfg_r[0] += 1

    # 最低位额外处理，进位计算等
    # 如果最低位存在进位或全0(直连前一位的进位)，加上之前的数位加法器配置，直到不存在进位
    if max_MSB_in >= LSB_OUT >= min_LSB_in:
        if cfg_m[LSB_OUT - min_LSB_in][4] >= 1 or cfg_m[LSB_OUT - min_LSB_in] == [0,0,0,0,0]:
            i = LSB_OUT - 1
            while max_MSB_in >= i >= min_LSB_in and cfg_m[i-min_LSB_in][3] >= 1:
                cfg_r = add_arrays(cfg_m[i-min_LSB_in], cfg_r)
                cfg_m_fix[i-min_LSB_in] = cfg_m[i-min_LSB_in]
                # 进位中不需要 add_carry
                if cfg_m[i-min_LSB_in][4] == 1:
                    cfg_r[4] -= 1
                    cfg_m_fix[i-min_LSB_in][4] = 0
                i -= 1
        
            # 进位中的最低位不需要异或
            cfg_r[2] -= 1 
            cfg_m_fix[i - min_LSB_in + 1][2] -= 1

            # 无符号数中，当 LSB_OUT 等于 max_MSB_in，输入两数的高位相差部分不需要计算 add_carry，只需要计算进位即可（1 1 0 2 1 0 1 -1 1）
            # if LSB_OUT == max_MSB_in and sign_out == 0:
            #     cfg_r[4] -= max_MSB_in - min_MSB_in
            #     for j in range(min_MSB_in, max_MSB_in):
            #         cfg_m_fix[j-min_LSB_in][4] = 0
            #     if cfg_m[min_MSB_in - min_LSB_in][4] == 0:
            #         cfg_r[4] += 1
                    
    # print(cfg_r)

    # 最高位额外处理
    # 最高位不需要计算是否需要进位
    if max_MSB_in >= MSB_OUT >= min_LSB_in:
        if cfg_m[MSB_OUT - min_LSB_in][3] >= 1:
            cfg_r[3] -= 1 
            cfg_m_fix[MSB_OUT-min_LSB_in][3] = 0
    
    if sign_out == 0:
        sign_bit = 0
    elif MSB_OUT >= max_MSB_in and (cfg_m[min_MSB_in - min_LSB_in + 1][4] != 0):
        sign_bit = MSB_OUT - max_MSB_in + 1
    else:
        sign_bit = 0        

    if LSB_OUT > max_MSB_in:
        cfg_r =[dwt_out,0,0,0,0]
        cfg_m_fix = []
        for i in range(len(cfg_m)):
            cfg_m_fix.append([0,0,0,0,0])
        sign_bit = 0

    # print(cfg_r) 
    # print("cfg_m_fix:", cfg_m_fix)

    tri_cry = 0
    for i in range(len(cfg_m_fix)):
        if max_MSB_in >= i + 1 + min_LSB_in >= min_LSB_in and cfg_m_fix[i] != [0,0,0,0,0]:
            if cfg_m_fix[i][3] == 1 and cfg_m_fix[i + 1][3] == 1:
                tri_cry += 1
                cfg_r[3] -= 2
                i += 1
    
    not_bit = 0
    not_bit = min(max_MSB_in, MSB_OUT) - max(min_LSB_in, LSB_OUT) + 1
    if not_bit < 0:
        not_bit = 0
    
    reg_bit = (dwt_out - cfg_r[0]) * n_pipelines
    return cfg_r[0], cfg_r[2], cfg_r[3], cfg_r[4], tri_cry, sign_bit, not_bit, reg_bit

# ---------------------------------------------------- MUL ----------------------------------------------------
def S2U_in(dwt_in, frac_in, sign_in):

    return

# 没有考虑 Delay 模块
def S2U_out(dwt_mul, frac_mul, dwt_out, frac_out, sign_in1, sign_in2):    
    out_bit = 0
    not_bit = 0
    xor_bit = 0
    gnd_bit = 0
    and4 = 0
    and3 = 0
    and2 = 0
    or_cnt = 0

    LSB_MUL = -frac_mul
    MSB_MUL = dwt_mul - frac_mul - 1
    LSB_OUT = -frac_out
    MSB_OUT = dwt_out - frac_out - 1

    if (sign_in1 or sign_in2) == 1:
        if LSB_OUT <= MSB_MUL + 1 and MSB_OUT >= LSB_MUL:
            if (sign_in1 and sign_in2) == 1:
                xor_bit = 1 # sign1 ^ sign2
            else:
                xor_bit = 0
            out_bit = min(MSB_MUL + 1, MSB_OUT) - max(LSB_MUL, LSB_OUT) + 1
            not_bit = min(MSB_MUL, MSB_OUT) - LSB_MUL + 1
        
        # ADD Part(故意这么写的)
        cfg_add = []
        for i in range(LSB_MUL, MSB_MUL + 2): # +2  for sign bit
            cfg_m = [0, 0, 0, 0] # [not, and, add, xor]
            if i == LSB_MUL:
                cfg_m[0] = 1
            elif i == MSB_MUL + 1:
                cfg_m[3] = 1
            else:
                cfg_m[2] = 1
            cfg_add.append(cfg_m)
        # print("cfg_add:", cfg_add)

        cfg_add_fix =[]
        for i in range(len(cfg_add)):
            cfg_add_fix.append([0, 0, 0, 0]) # [not, and, add, xor]

        for i in range(LSB_OUT, MSB_OUT + 1):
            if i >= LSB_MUL and i <= MSB_MUL + 1:
                cfg_add_fix[i - LSB_MUL] = cfg_add[i - LSB_MUL]
        
        # 非截断范围内的运算只需要进位结果不需要加法
        if MSB_MUL + 1 >= LSB_OUT >= LSB_MUL and cfg_add_fix[LSB_OUT - LSB_MUL][2] == 1:
            for i in range(LSB_MUL + 1, LSB_OUT):
                cfg_add_fix[i - LSB_MUL][2] = 0
                cfg_add_fix[i - LSB_MUL][1] = 1
        
        # 最高位只需要异或不需要其他运算
        if MSB_MUL + 1 >= MSB_OUT > LSB_MUL:
            cfg_add_fix[MSB_OUT - LSB_MUL][2] = 0
            cfg_add_fix[MSB_OUT - LSB_MUL][3] = 1
        # print("cfg_add_fix:", cfg_add_fix)
        
        cfg_r = [0, 0, 0, 0] # [not, and, add, xor] of result
        for i in range(len(cfg_add_fix)):
            cfg_r = add_arrays(cfg_add_fix[i], cfg_r)
        # print("cfg_r:", cfg_r)
        
        
        if LSB_OUT < LSB_MUL:
            gnd_bit = min(LSB_MUL, MSB_OUT + 1) - LSB_OUT
        # if MSB_OUT > MSB_MUL + 1:
        #     gnd_bit += MSB_OUT - (MSB_MUL + 1)
        if LSB_OUT > MSB_MUL + 1:
            gnd_bit = dwt_out
        
        # 处理只取 LSB_MUL 时，取反加一后仍是原值
        if MSB_OUT == LSB_MUL and dwt_mul < 4:
            xor_bit = cfg_r[3]
            out_bit = 0
            not_bit = 0
        elif MSB_OUT == LSB_MUL:
            not_bit = 1
        else:
            xor_bit += cfg_r[3]
            not_bit += cfg_r[0]
        
        # 处理只取 MSB_MUL + 1 时
        if LSB_OUT == MSB_MUL + 1:
            and4 = (dwt_mul + 1) // 4 
            and3 = (dwt_mul + 1 - 4 * and4) // 3
            and2 = (dwt_mul + 1 - 4 * and4 - 3 * and3) // 2
            or_cnt = and4 + and3 + and2 + (dwt_mul + 1 - 4*and4 - 3*and3 - 2*and2)
            xor_bit = 1

        if dwt_mul < 4:
            out_bit = 0
        
    else:
        cfg_r = [0, 0, 0, 0]
    
    Fxp_bit = dwt_out - gnd_bit
            
    return out_bit, not_bit, xor_bit, cfg_r[2], cfg_r[1], and4, and3, and2, or_cnt, Fxp_bit, gnd_bit

# 统计需要多少 ha 和 fa
def ha_fa_s(op):
    ha = 0
    fa = 0
    dir_bit = 0
    op_l = op # 剩余操作数

    if op_l == 1:
        dir_bit = 1

    while op_l > 1 :
        fa += op_l // 3
        op_l = op_l % 3 + op_l // 3
        if op_l <= 2:
            ha += op_l // 2
            op_l = op_l % 2 + op_l // 2
    
    return ha, fa, dir_bit

# 纯乘法器
def MUL_op(dwt_in1, dwt_in2, dwt_out):
    and_bit = 0
    ha_bit = 0
    fa_bit = 0
    dir_bit = 0
    xor_bit = 0
    gnd_bit = 0
    
    
    # 竖型乘法每列有几个数要相加
    op =[]
    for i in range(1, dwt_in1 + dwt_in2):
        if i == 1:
            op.append(1)
        elif i == dwt_in1 + dwt_in2 - 1:
            op.append(1)
        else:
            op.append(min(dwt_in1 + dwt_in2 - i, min(dwt_in1, dwt_in2), i))
    
    for i in range(dwt_out):
        if i < len(op):
            and_bit += op[i]
    # print(op)
    
    ha_temp = 0
    fa_temp = 0
    dir_temp = 0
    for i in range (dwt_out):
        if i < len(op):
            ha_temp, fa_temp, dir_temp = ha_fa_s(op[i])
            # 进位
            if i + 1 < len(op):
                op[i+1] += ha_temp + fa_temp
            # 最高位处理进位
            if i == dwt_out - 1:
                xor_bit = op[i] - 1
            else:
                ha_bit += ha_temp
                fa_bit += fa_temp
                dir_bit += dir_temp
    
    if min(dwt_in1, dwt_in2) == 1:
        if dwt_out > max(dwt_in1, dwt_in2):
            gnd_bit = dwt_out - max(dwt_in1, dwt_in2)
    elif dwt_out > (dwt_in1 + dwt_in2) :
        gnd_bit = dwt_out - dwt_in1 - dwt_in2

    return  and_bit, ha_bit, fa_bit, xor_bit, gnd_bit

if __name__ == '__main__':
    os.chdir(os.path.dirname(__file__))
    # print(adder_config_v2(1,-1,1,2,2,1,2,-1,1))
    # print("gnd, dir, xor, carry, add_carry, tri_cry, sign_bit, reg")

    # print(S2U_out(9, 2, 9, 2, 1, 0)) # dwt_mul, frac_mul, dwt_out, frac_out, sign_in1, sign_in2
    # print("out_bit,", "not_bit,", "xor_bit,", "add_bit,", "and_bit,", "gnd_bit")

    # print("and_bit, ha_bit, fa_bit, xor_bit")
    # print(MUL_op(3, 3, 5))

    # dwt_mul, frac_mul, dwt_out, frac_out, sign_in1, sign_in2
    # print(Comp_cfg(3, 1, 1, 3, 1, 1))
    