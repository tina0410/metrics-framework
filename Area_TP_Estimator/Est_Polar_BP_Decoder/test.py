import math

def ModuleType1_control(width, N, M):
    # 计算中间变量
    t3 = int(math.log(N, 2)) - 1
    tm = t3 * int(N / M)
    if tm & (tm - 1) == 0:
        m = int(math.log(tm, 2))
    else:
        m = int(math.log(tm, 2)) + 1
    num_switch = int(math.log(int(N / M), 2))
    t = num_switch + 3
    # t=4
    if t & (t - 1) == 0:
        t2 = int(math.log(t, 2))
    else:
        t2 = int(math.log(t, 2)) + 1
    # t2 = 3
    temp1 = 0
    for i in range(0, num_switch):
        temp1 = temp1 + int(math.pow(2, num_switch - i))
    num_state = (2 * t3 + 1) * int(N / M) + temp1 + 2
    if num_state & (num_state - 1) == 0:
        t4 = int(math.log(num_state, 2))
    else:
        t4 = int(math.log(num_state, 2)) + 1
    for_state = t3 * int(N / M) + int(temp1 / 2)

    # 输出 Verilog 模块
    temp1 = 0
    for i in range(0, num_switch):
        temp1 = temp1 + int(math.pow(2, num_switch - i))

    state = num_state - 1 - int(N / M) - 1
    state_dec = num_state - int(N / M), num_state - 1

    if 0 < num_switch < t3:
        temp3 = 0
        for i in range(0, num_switch):
            temp2 = int(math.pow(2, num_switch - i))
            for index in range(1, int(N / M) + int(temp2 / 2) + 1):
                if i != 0 and index <= int(N/M):
                    ctr_mux11 += 1
                else:
                    ctr_mux10 += 1
                if index == int(N / M) + int(temp2 / 2):
                    for j in range(0, i + 1):
                        ctr_switch0 += 1
                    for j in range(i + 1, num_switch):
                        if j == i + 1:
                            ctr_switch1 += 1
                        else:
                            ctr_switch0 += 1
                else:
                    for j in range(0, num_switch):
                        ctr_switch0 += 1
                        
                if index < int(temp2 / 2) + 1:
                    we0 += 1
                    wr_addr0 += 1
                else:
                    we1 += 1
            temp3 = int(N / M) + int(temp2 / 2) + temp3
        
        for i in range(num_switch, t3):
            for index in range(1, int(N / M) + 1):
                ctr_mux11 += 1
                ctr_mux20 += 0
                ctr_mux30 += 0
                for j in range(0, num_switch):
                    ctr_switch0 += 1
                we1 += 1
        
        for i in range(0, t3 - num_switch):
            for index in range(1, int(N / M) + 1):
                if i == 0:
                    ctr_mux12 += 1
                else:
                    ctr_mux11 += 1
                ctr_mux21 += 1
                ctr_mux31 += 1
                if i == t3 - num_switch - 1 and index == int(N / M):
                    for j in range(0, num_switch - 1):
                        ctr_switch0 += 0
                    ctr_switch1 += 1
                else:
                    for j in range(0, num_switch):
                        ctr_switch0 += 0
                we1 += 1
        
        temp4 = 0
        for i in range(0, num_switch):
            temp2 = int(math.pow(2, i + 1))
            for index in range(1, int(N / M) + int(temp2 / 2) + 1):
                if index <= int(N/M):
                    ctr_mux1 += 1
                else:
                    ctr_mux10 += 1
                if index == int(N / M) + int(temp2 / 2):
                    for j in range(num_switch - 1, i, -1):
                        if j == i + 1:
                            ctr_switch1 += 1
                        else:
                            ctr_switch0 += 1
                    for j in range(i, -1, -1):
                        ctr_switch0 += 1
                else:
                    for j in range(0, num_switch):
                        ctr_switch0 += 1
                if index < int(temp2 / 2) + 1:
                    we0 += 1
                    wr_addr0 += 1
                else:
                    we1 += 1
            temp4 = int(N / M) + int(temp2 / 2) + temp4
    
    elif num_switch == t3:
        temp5 = 0
        for i in range(0, num_switch):
            temp2 = int(math.pow(2, num_switch - i))
            for index in range(1, int(N / M) + int(temp2 / 2) + 1):
                if i != 0 and index <= int(N / M):
                    ctr_mux11 += 1
                else:
                    ctr_mux10 += 1
                    pass
                if i != num_switch - 1 and index == int(N / M) + int(temp2 / 2):
                    for j in range(0, i + 1):
                        ctr_switch0 += 0
                    for j in range(i + 1, num_switch):
                        if j == i + 1:
                            ctr_switch1 += 1
                        else:
                            ctr_switch0 += 0
                elif i == num_switch - 1 and index == int(N / M) + int(temp2 / 2):
                    for j in range(0, i):
                        ctr_switch0 += 0
                    ctr_switch1 += 1
                else:
                    for j in range(0, num_switch):
                        ctr_switch0 += 1
                if index < int(temp2 / 2) + 1:
                    we0 += 1
                else:
                    we1 += 1
                if index < int(N / M) + 1:
                    #/             re_addr = `i * int(N/M) + index - 1`;
                    pass
                else:
                    #/             re_addr = 0;
                    pass
                #/             flag = 0;
                #/             out_valid = 0;
                #/             next_state = state`temp5+index+1`;
                #/         end
                pass
            temp5 = int(N / M) + int(temp2 / 2) + temp5
        
        temp6 = 0
        for i in range(0, num_switch):
            temp2 = int(math.pow(2, i + 1))
            for index in range(1, int(N / M) + int(temp2 / 2) + 1):
                #/         state`temp6 + index + for_state`: begin
                if i == 0 and index <= int(N / M):
                    #/             ctr_mux1 = 2;
                    pass
                elif i != 0 and index <= int(N / M):
                    #/             ctr_mux1 = 1;
                    pass
                else:
                    #/             ctr_mux1 = 0;
                    pass
                #/             ctr_mux2 = `num_switch+1-i`;
                #/             ctr_mux3 = `num_switch+1-i`;
                if index == int(N / M) + int(temp2 / 2):
                    for j in range(num_switch - 1, i, -1):
                        if j == i + 1:
                            #/             ctr_switch`num_switch - j` = 1;
                            pass
                        else:
                            #/             ctr_switch`num_switch - j` = 0;
                            pass
                    for j in range(i, -1, -1):
                        #/             ctr_switch`num_switch - j` = 0;
                        pass
                else:
                    for j in range(0, num_switch):
                        #/             ctr_switch`j+1` = 0;
                        pass
                if index < int(temp2 / 2) + 1:
                    #/             we = 0;
                    #/             wr_addr = 0;
                    pass
                else:
                    #/             we = 1;
                    #/             wr_addr = `(num_switch-1-i)*int(N/M) + index - int(temp2/2) - 1`;
                    pass
                if index < int(N / M) + 1:
                    #/             re_addr = `(num_switch-1-i)*int(N/M) + index - 1`;
                    pass
                else:
                    #/             re_addr = 0;
                    pass
                #/             flag = 0;
                #/             out_valid = 0;
                if i == num_switch - 1 and index == int(N / M) + int(temp2 / 2):
                    #/             next_state = state_judge;
                    #/         end
                    pass
                else:
                    #/             next_state = state`temp6 + index + for_state + 1`;
                    #/         end
                    pass
                pass
            temp6 = int(N / M) + int(temp2 / 2) + temp6
    
    else:
        for index in range(1, 2 * t3 + 1):
            #/         state`index`: begin
            if index == 1:
                #/             ctr_mux1 = 0;
                pass
            elif index == t3 + 1:
                #/             ctr_mux1 = 2;
                pass
            else:
                #/             ctr_mux1 = 1;
                pass
            if index < t3 + 1:
                #/             ctr_mux2 = 0;
                #/             ctr_mux3 = 0;
                pass
            else:
                #/             ctr_mux2 = 1;
                #/             ctr_mux3 = 1;
                pass
            if index < t3 + 1:
                #/             we = 1;
                #/             wr_addr = `index-1`;
                #/             re_addr = `index-1`;
                pass
            else:
                #/             we = 1;
                #/             wr_addr = `2*t3-index`;
                #/             re_addr = `2*t3-index`;
                pass
            #/             flag = 0;
            #/             out_valid = 0;
            if index == 2 * t3:
                #/             next_state = state_judge;
                #/         end
                pass
            else:
                #/             next_state = state`index+1`;
                #/         end
                pass
            pass

    #/         state_judge: begin
    #/             ctr_mux1 = 0;
    #/             ctr_mux2 = 0;
    #/             ctr_mux3 = 0;
    for j in range(0, num_switch):
        if j == 0:
            #/             ctr_switch1 = 1;
            pass
        else:
            #/             ctr_switch`j+1` = 0;
            pass
    #/             we = 0;
    #/             wr_addr = 0;
    #/             re_addr = 0;
    #/             flag = 1;
    #/             out_valid = 0;
    #/             next_state = (early_stop) ? state_dec0 : state1;
    #/         end
    #/ 
    for index in range(1, int(N / M) + 1):
        #/         state_dec`index-1`: begin
        #/             ctr_mux1 = 3;
        #/             ctr_mux2 = `num_switch+2`;
        #/             ctr_mux3 = `num_switch+2`;
        for j in range(0, num_switch):
            #/             ctr_switch`j+1` = 0;
            pass
        #/             we = 0;
        #/             wr_addr = 0;
        #/             re_addr = `index-1`;
        if index == int(N / M):
            #/             flag = 0;
            #/             out_valid = 1;
            #/             next_state = state_init;
            #/         end
            pass
        else:
            #/             flag = 0;
            #/             out_valid = 0;
            #/             next_state = state_dec`index`;
            #/         end
            pass
        pass
    
    #/         default: begin
    #/             ctr_mux1 = 0;
    #/             ctr_mux2 = 0;
    #/             ctr_mux3 = 0;
    for j in range(0, num_switch):
        #/             ctr_switch`j+1` = 0;
        pass
    #/             we = 0;
    #/             wr_addr = 0;
    #/             re_addr = 0;
    #/             flag = 0;
    #/             out_valid = 0;
    #/             next_state = state_init;
    #/         end
    #/     endcase
    #/ end
    #/ endmodule
    pass