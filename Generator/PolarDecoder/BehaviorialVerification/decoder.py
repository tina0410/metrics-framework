import pytv
from pytv import convert
from pytv import moduleloader
from utils import run_iverilog_flow, merge_files, move_and_rename_file, run_cpp_flow
from cpp_modules import ModuleConfig
import os
import math

@convert
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
    if t & (t - 1) == 0:
        t2 = int(math.log(t, 2))
    else:
        t2 = int(math.log(t, 2)) + 1
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
    #/ module control (
    #/     input clk,
    #/     input rst,
    #/     input early_stop,
    #/     output reg [1:0] ctr_mux1,
    #/     output reg [`t2-1`:0] ctr_mux2,
    #/     output reg [`t2-1`:0] ctr_mux3,
    temp1 = 0
    for i in range(0, num_switch):
        temp1 = temp1 + int(math.pow(2, num_switch - i))
        #/     output reg ctr_switch`i+1`,
        pass
    #/     output reg we,
    #/     output reg [`m-1`:0] wr_addr,
    #/     output reg [`m-1`:0] re_addr,
    #/     output reg flag,
    #/     output reg out_valid
    #/ );
    #/ 
    #/ localparam state_init=0,
    for i in range(1, num_state - 1 - int(N / M)):
        #/     state`i`=`i`,
        pass
    #/     state_judge=`num_state-1-int(N/M)`,
    for i in range(num_state - int(N / M), num_state - 1):
        #/     state_dec`i - (num_state - int(N/M))`=`i`,
        pass
    #/     state_dec`int(N/M)-1`=`num_state-1`;
    #/ 
    #/ reg [`t4-1`:0] current_state;
    #/ reg [`t4-1`:0] next_state;
    #/ 
    #/ always @(posedge clk or negedge rst) begin
    #/     if (!rst)
    #/         current_state <= state_init;
    #/     else
    #/         current_state <= next_state;
    #/ end
    #/ 
    #/ always @(current_state or early_stop) begin
    #/     case (current_state)
    #/         state_init: begin
    #/             ctr_mux1 = 0;
    #/             ctr_mux2 = 0;
    #/             ctr_mux3 = 0;
    #/             we = 0;
    #/             wr_addr = 0;
    #/             re_addr = 0;
    #/             flag = 0;
    #/             out_valid = 0;
    for i in range(0, num_switch):
        if i == 0:
            #/             ctr_switch1 = 1;
            pass
        else:
            #/             ctr_switch`i+1` = 0;
            pass
    #/             next_state = state1;
    #/         end
    #/ 
    if 0 < num_switch < t3:
        temp3 = 0
        for i in range(0, num_switch):
            temp2 = int(math.pow(2, num_switch - i))
            for index in range(1, int(N / M) + int(temp2 / 2) + 1):
                #/         state`temp3+index`: begin
                if i != 0 and index <= int(N/M):
                    #/             ctr_mux1 = 1;
                    pass
                else:
                    #/             ctr_mux1 = 0;
                    pass
                #/             ctr_mux2 = `i+2`;
                #/             ctr_mux3 = `i+2`;
                if index == int(N / M) + int(temp2 / 2):
                    for j in range(0, i + 1):
                        #/             ctr_switch`j+1` = 0;
                        pass
                    for j in range(i + 1, num_switch):
                        if j == i + 1:
                            #/             ctr_switch`j+1` = 1;
                            pass
                        else:
                            #/             ctr_switch`j+1` = 0;
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
                    #/             wr_addr = `i * int(N/M) + index - int(temp2/2) - 1`;
                    pass
                if index < int(N / M) + 1:
                    #/             re_addr = `i * int(N/M) + index - 1`;
                    pass
                else:
                    #/             re_addr = 0;
                    pass
                #/             flag = 0;
                #/             out_valid = 0;
                #/             next_state = state`temp3+index+1`;
                #/         end
                pass
            temp3 = int(N / M) + int(temp2 / 2) + temp3
        
        for i in range(num_switch, t3):
            for index in range(1, int(N / M) + 1):
                #/         state`i * int(N/M) + int(temp1/2) + index`: begin
                #/             ctr_mux1 = 1;
                #/             ctr_mux2 = 0;
                #/             ctr_mux3 = 0;
                for j in range(0, num_switch):
                    #/             ctr_switch`j+1` = 0;
                    pass
                #/             we = 1;
                #/             wr_addr = `i * int(N/M) + index - 1`;
                #/             re_addr = `i * int(N/M) + index - 1`;
                #/             flag = 0;
                #/             out_valid = 0;
                #/             next_state = state`i * int(N/M) + int(temp1/2) + index + 1`;
                #/         end
                pass
        
        for i in range(0, t3 - num_switch):
            for index in range(1, int(N / M) + 1):
                #/         state`i * int(N/M) + for_state + index`: begin
                if i == 0:
                    #/             ctr_mux1 = 2;
                    pass
                else:
                    #/             ctr_mux1 = 1;
                    pass
                #/             ctr_mux2 = 1;
                #/             ctr_mux3 = 1;
                if i == t3 - num_switch - 1 and index == int(N / M):
                    for j in range(0, num_switch - 1):
                        #/             ctr_switch`j+1` = 0;
                        pass
                    #/             ctr_switch`num_switch` = 1;
                    pass
                else:
                    for j in range(0, num_switch):
                        #/             ctr_switch`j+1` = 0;
                        pass
                #/             we = 1;
                #/             wr_addr = `(t3-1-i) * int(N/M) + index - 1`;
                #/             re_addr = `(t3-1-i) * int(N/M) + index - 1`;
                #/             flag = 0;
                #/             out_valid = 0;
                #/             next_state = state`i * int(N/M) + for_state + index + 1`;
                #/         end
                pass
        
        temp4 = 0
        for i in range(0, num_switch):
            temp2 = int(math.pow(2, i + 1))
            for index in range(1, int(N / M) + int(temp2 / 2) + 1):
                #/         state`temp4 + index + (t3 - num_switch) * int(N/M) + for_state`: begin
                if index <= int(N/M):
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
                    #/             next_state = state`temp4 + index + (t3 - num_switch)*int(N/M) + for_state + 1`;
                    #/         end
                    pass
                pass
            temp4 = int(N / M) + int(temp2 / 2) + temp4
    
    elif num_switch == t3:
        temp5 = 0
        for i in range(0, num_switch):
            temp2 = int(math.pow(2, num_switch - i))
            for index in range(1, int(N / M) + int(temp2 / 2) + 1):
                #/         state`temp5+index`: begin
                if i != 0 and index <= int(N / M):
                    #/             ctr_mux1 = 1;
                    pass
                else:
                    #/             ctr_mux1 = 0;
                    pass
                #/             ctr_mux2 = `i+2`;
                #/             ctr_mux3 = `i+2`;
                if i != num_switch - 1 and index == int(N / M) + int(temp2 / 2):
                    for j in range(0, i + 1):
                        #/             ctr_switch`j+1` = 0;
                        pass
                    for j in range(i + 1, num_switch):
                        if j == i + 1:
                            #/             ctr_switch`j+1` = 1;
                            pass
                        else:
                            #/             ctr_switch`j+1` = 0;
                            pass
                elif i == num_switch - 1 and index == int(N / M) + int(temp2 / 2):
                    for j in range(0, i):
                        #/             ctr_switch`j+1` = 0;
                        pass
                    #/             ctr_switch`num_switch` = 1;
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
                    #/             wr_addr = `i * int(N/M) + index - int(temp2/2) - 1`;
                    pass
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


@ convert
def ModuleAdd(width):
    #/ module add (
    #/ input [`width`-1:0] in1,
    #/ input [`width`-1:0] in2,
    #/ output [`width`-1:0] out);
    #/ wire [`width`:0] temp1;
    #/ wire [`width`:0] temp2;
    #/ wire [`width`:0] temp3;
    #/ wire [`width`-1:0] temp4;
    #/ assign temp1 = {in1[`width`-1],in1};
    #/ assign temp2 = {in2[`width`-1],in2};
    #/ assign temp3 = temp1 + temp2;
    #/ assign temp4 = (temp3[`width`:`width`-1] == 2'b01)?{1'b0,{(`width`-1){1'b1}}}:(temp3[`width`:`width`-1] == 2'b10)?{1'b1,{(`width`-1){1'b0}}}:in1 + in2;
    #/ assign out = (temp4 == {1'b1,{(`width`-1){1'b0}}})?{1'b1,{(`width`-2){1'b0}},1'b1}:temp4;
    #/ endmodule
    pass
 
    
@ convert
def ModuleType1_BCB(algo, N, M, width):
    if algo == 'MS':
        #/ module BCB (
        #/ input [`width`-1:0] up0,
        #/ input [`width`-1:0] up1,
        #/ input [`width`-1:0] down0,
        #/ input [`width`-1:0] down1,
        #/ output [`width`-1:0]out0,
        #/ output [`width`-1:0] out1);
        #/ wire sign1,sign2;
        #/ wire [`width`-1:0] temp;
        #/ wire [`width`-1:0] result;
        #/ wire [`width`-2:0] abs1,abs2,abs3;
        #/ wire [`width`-2:0] value1,value2;
        #/ assign sign1=up0[`width`-1] ^ temp[`width`-1];
        #/ assign sign2=up0[`width`-1] ^ down0[`width`-1];
        #/ assign abs1=(up0[`width`-1]==1'b0)?up0[`width`-2:0]:(1'b1+~ up0[`width`-2:0]);
        #/ assign abs2=(temp[`width`-1]==1'b0)?temp[`width`-2:0]:(1'b1+~ temp[`width`-2:0]);
        #/ assign abs3=(down0[`width`-1]==1'b0)?down0[`width`-2:0]:(1'b1+~ down0[`width`-2:0]);
        #/ assign value1=(abs1 < abs2)?abs1:abs2;
        #/ assign value2=(abs1 < abs3)?abs1:abs3;
        #/ assign out0 = (value1)?(sign1)?{sign1,~value1+1'b1}:{sign1,value1}:{(`width`){{1'b0}}};
        #/ assign result = (value2)?(sign2)?{sign2,~value2+1'b1}:{sign2,value2}:{(`width`){{1'b0}}};
        PORTS_add1 = {
        'in1':'up1',
        'in2':'down1',
        'out': 'temp'
        }
        ModuleAdd(width=width, PORTS = PORTS_add1)
        PORTS_add2 = {
        'in1':'up1',
        'in2':'result',
        'out': 'out1'
        }
        ModuleAdd(width=width, PORTS = PORTS_add2)
        #/ endmodule
    if algo == 'SMS':
        #/ module BCB (
        #/ input [`width`-1:0] up0,
        #/ input [`width`-1:0] up1,
        #/ input [`width`-1:0] down0,
        #/ input [`width`-1:0] down1,
        #/ output [`width`-1:0]out0,
        #/ output [`width`-1:0] out1);
        #/ wire sign1,sign2;
        #/ wire [`width`-1:0] temp,temp1,temp2;
        #/ wire [`width`-1:0] result;
        #/ wire [`width`-2:0] abs1,abs2,abs3;
        #/ wire [`width`-2:0] minvalue1,minvalue2;
        #/ wire [`width`-1:0] offset;
        #/ wire [`width`-1:0] offsetvalue1,offsetvalue2;
        #/ wire [`width`-1:0] comvalue1,comvalue2;
        #/ assign offset={`width`{{1'b1}}};
        #/ assign sign1=up0[`width`-1] ^ temp[`width`-1];
        #/ assign sign2=up0[`width`-1] ^ down0[`width`-1];
        #/ assign abs1=(up0[`width`-1]==1'b0)?up0[`width`-2:0]:(1'b1+~ up0[`width`-2:0]);
        #/ assign abs2=(temp[`width`-1]==1'b0)?temp[`width`-2:0]:(1'b1+~ temp[`width`-2:0]);
        #/ assign abs3=(down0[`width`-1]==1'b0)?down0[`width`-2:0]:(1'b1+~ down0[`width`-2:0]);
        #/ assign minvalue1=(abs1 < abs2)?abs1:abs2;
        #/ assign minvalue2=(abs1 < abs3)?abs1:abs3;
        #/ assign temp1={1'b0,minvalue1};
        #/ assign temp2={1'b0,minvalue2};
        #/ assign comvalue1 = (offsetvalue1[`width`-1])?{(`width`){1'b0}}:offsetvalue1;
        #/ assign comvalue2 = (offsetvalue2[`width`-1])?{(`width`){1'b0}}:offsetvalue2;
        #/ assign out0 = (comvalue1)?(sign1)?{sign1,~comvalue1[`width`-2:0]+1'b1}:comvalue1:{(`width`){{1'b0}}};
        #/ assign result = (comvalue2)?(sign2)?{sign2,~comvalue2[`width`-2:0]+1'b1}:comvalue2:{(`width`){{1'b0}}};
        PORTS_add1 = {
        'in1':'up1',
        'in2':'down1',
        'out': 'temp'
        }
        ModuleAdd(width=width, PORTS = PORTS_add1)
        PORTS_add2 = {
        'in1':'temp1',
        'in2':'offset',
        'out': 'offsetvalue1'
        }
        ModuleAdd(width=width, PORTS = PORTS_add2)
        PORTS_add3 = {
        'in1':'temp2',
        'in2':'offset',
        'out': 'offsetvalue2'
        }
        ModuleAdd(width=width, PORTS = PORTS_add3)
        PORTS_add4 = {
        'in1':'up1',
        'in2':'result',
        'out': 'out1'
        }
        ModuleAdd(width=width, PORTS = PORTS_add4)
        #/ endmodule
    pass


# convert to pytv format
@ convert
def ModuleType1_mux1(width, N, M):
    #/ module mux1 (
    #/ input [1:0] ctr,
    #/ input [`M*width`-1:0] in1,
    #/ input [`M*width`-1:0] in2,
    #/ input [`M*width`-1:0] in3,
    #/ input [`M*width`-1:0] in4,
    #/ output reg [`M*width`-1:0] out1,
    #/ output reg [`M*width`-1:0] out2
    #/ );
    #/ always @ (*)
    #/ case (ctr)
    #/ 2'b00: begin out1 = in1; out2 = in3; end
    #/ 2'b01: begin out1 = in4; out2 = in3; end
    #/ 2'b10: begin out1 = in2; out2 = in3; end
    #/ 2'b11: begin out1 = in3; out2 = in1; end
    #/ endcase
    #/ endmodule
    pass


# convert to pytv format
@ convert
def ModuleType1_mux2(width, N, M):
    num_switch = int(math.log(int(N / M), 2))
    t = num_switch + 3
    if t & (t - 1) == 0:
        t1 = int(math.log(t, 2))
    else:
        t1 = int(math.log(t, 2)) + 1
    #/ module mux2 (
    #/ input [`t1`-1:0] ctr,
    #/ input [`M*width`-1:0] in,
    for i in range(1, t):
        #/ output [`M*width`-1:0] out`i`,
        pass
    #/ output [`M*width`-1:0] out`t`
    #/ );
    for i in range(0, t):
        #/ assign out`i+1` = (ctr==`i`)?in:{(`M*width`){1'b0}};
        pass
    #/ endmodule
    pass

    
# convert to pytv format
@ convert
def ModuleType1_mux3(width, N, M):
    num_switch = int(math.log(int(N / M), 2))
    t = num_switch + 3
    if t & (t - 1) == 0:
        t1 = int(math.log(t, 2))
    else:
        t1 = int(math.log(t, 2)) + 1
    #/ module mux3 (
    #/ input [`t1`-1:0] ctr,
    for i in range(1, t + 1):
        #/ input [`M*width`-1:0] in`i`,
        pass
    #/ output reg [`M*width`-1:0] out
    #/ );
    #/ always @ (*)
    #/ case (ctr)
    for i in range(0, t):
        #/ `i`: out = in`i+1`;
        pass
    if t & (t - 1) != 0:
        #/ default: out = {(`M*width`){1'b0}};
        pass
    #/ endcase
    #/ endmodule
    pass

    
# convert to pytv format
@ convert
def ModuleType1_delay_reg(width, N, M):
    #/ module delay_reg (
    #/ input clk,
    #/ input [`M*width`-1:0] in,
    #/ output [`M*width`-1:0] out1,
    #/ output [`N*width`-1:0] out2
    #/ );
    if N == M:
        #/   reg [`M*width`-1:0] temp;
        #/   always @(posedge clk)
        #/   begin
        #/     temp <= in;
        #/   end
        #/   assign out1 = temp;
        #/   assign out2 = temp;
        #/   endmodule
        pass
    else:
        #/   reg [`M*width`-1:0] temp[`int(N/M)-1`:0];
        #/   always @(posedge clk)
        #/   begin
        #/     temp[0] <= in;
        for i in range(1, int(N / M)):
            #/     temp[`i`] <= temp[`i`-1];
            pass
        #/   end
        #/   assign out1 = temp[`int(N/M)-1`];
        #/   assign out2 = {
        for i in range(0, int(N / M) - 1):
            #/     temp[`i`],
            pass
        #/     temp[`int(N/M)-1`]};
        #/   endmodule

    
# convert to pytv format
@ convert
def ModuleType1_memory(width, N, M):
    t = int(math.log(N, 2)) - 1
    tm = t * int(N / M)
    if tm & (tm - 1) == 0:
        m = int(math.log(tm, 2))
    else:
        m = int(math.log(tm, 2)) + 1
    #/ module memory (
    #/ input clk,
    #/ input rst,
    #/ input we,
    #/ input [`m`-1:0] wr_addr,
    #/ input [`m`-1:0] re_addr,
    #/ input [`M*width`-1:0] in,
    #/ output [`M*width`-1:0] out
    #/ );
    #/ reg [`M*width`-1:0] temp[`tm`-1:0];
    #/ always @(posedge clk or negedge rst)
    #/ begin
    #/   if(!rst)
    #/   begin
    for i in range(0, tm):
        #/     temp[`i`] <= {(`M*width`){1'b0}};
        pass
    #/   end
    #/   else if(we)
    #/     temp[wr_addr] <= in;
    #/   end
    #/   assign out = temp[re_addr];
    #/ endmodule


# convert to pytv format
@ convert
def ModuleType1_perm(width, N, M):
    #/ module perm (
    #/ input [`M*width`-1:0] in,
    #/ output [`M*width`-1:0] out
    #/ );
    for i in range(0, M, 2):
        #/ assign out[`i+1`*`width`-1:`i`*`width`] = in[`int(i/2)+1`*`width`-1:`int(i/2)`*`width`];
        #/ assign out[`i+2`*`width`-1:`i+1`*`width`] = in[`int((i+M)/2)+1`*`width`-1:`int((i+M)/2)`*`width`];
        pass
    #/ endmodule
    pass


# convert to pytv format
@ convert
def ModuleType1_reverse_perm(width, N, M):
    #/ module reverse_perm (
    #/ input [`M*width`-1:0] in,
    #/ output [`M*width`-1:0] out
    #/ );
    for i in range(0, M, 2):
        #/ assign out[`int(i/2)+1`*`width`-1:`int(i/2)`*`width`] = in[`i+1`*`width`-1:`i`*`width`];
        #/ assign out[`int((i+M)/2)+1`*`width`-1:`int((i+M)/2)`*`width`] = in[`i+2`*`width`-1:`i+1`*`width`];
        pass
    #/ endmodule
    pass

    
# convert to pytv format
@ convert
def ModuleType1_gen_bcb(width, N, M, algo):
    #/ module gen_BCB (
    #/ input [`M*width`-1:0] up,
    #/ input [`M*width`-1:0] down,
    #/ output [`M*width`-1:0] out
    #/ );
    for i in range(0, int(M / 2)):
       PORTS_bcb = {
           "up0": f"up[{i*2+1}*{width}-1:{i*2}*{width}]",
           "up1": f"up[{i*2+2}*{width}-1:{i*2+1}*{width}]",
           "down0": f"down[{i*2+1}*{width}-1:{i*2}*{width}]",
           "down1": f"down[{i*2+2}*{width}-1:{i*2+1}*{width}]",
           "out0": f"out[{i*2+1}*{width}-1:{i*2}*{width}]",
           "out1": f"out[{i*2+2}*{width}-1:{i*2+1}*{width}]"
       }
       ModuleType1_BCB(width=width, algo=algo, N=N, M=M, PORTS=PORTS_bcb)
       pass
    #/ endmodule
    pass


# convert to pytv 
@ convert
def ModuleType1_gen_switch(width, N, M, number, count):
    t = int(math.log(number, 2))
    #/ module gen_switch (
    #/ input clk,
    #/ input ctr,
    #/ input [`M*width`-1:0] in,
    #/ output [`M*width`-1:0] out
    #/ );
    #/ wire [`count`-1:0] cnt;
    PORTS_counter = {
        'clk': 'clk',
        'ctr': 'ctr',
        'cnt': 'cnt'
    }
    ModuleType1_counter(N=N, M=M, count=count, value=0, PORTS=PORTS_counter)
    for i in range(0, int(M / 2), 1):
        PORTS_switch = {
            'clk': 'clk',
            'cnt': 'cnt',
            'in': f'in[{(i+1)*2*width-1}:{i*2*width}]',
            'out': f'out[{(i+1)*2*width-1}:{i*2*width}]'
        }
        ModuleType1_switch(width=width, N=N, M=M, number=number, count=count, PORTS=PORTS_switch)
        pass
    #/ endmodule
    pass

    
# convert to pytv 
@convert
def ModuleType1_gen_switch2(width, N, M):
    #/ module gen_switch2 (
    #/ input clk,
    #/ input ctr,
    #/ input [`M*width`-1:0] in,
    #/ output [`M*width`-1:0] out
    #/ );
    #/ wire cnt;
    PORTS_counter = {
    'clk':'clk',
    'ctr':'ctr',
    'cnt':'cnt'
    }
    ModuleType1_counter(N=N, M=M, count=1, value=0, PORTS=PORTS_counter)
    for i in range(0, int(M / 2), 1):
        PORTS_switch2 = {
            'clk': 'clk',
            'cnt': 'cnt',
            'in': f'in[{(i+1)*2*width-1}:{i*2*width}]',
            'out': f'out[{(i+1)*2*width-1}:{i*2*width}]'
        }
        ModuleType1_switch2(width=width, N=N, M=M, PORTS=PORTS_switch2)
        pass
    #/ endmodule


# convert to pytv 
@convert
def ModuleType1_switch(width, N, M, number, count):
    t = int(math.log(number, 2))
    #/ module switch (
    #/ input clk,
    #/ input [`count`-1:0] cnt,
    #/ input [`2*width`-1:0] in,
    #/ output [`2*width`-1:0] out
    #/ );
    #/ reg [`number*width`-1:0] temp;
    #/ always @(posedge clk)
    #/ begin
    #/ temp[`width`-1:0]<=in[2*`width`-1:`width`];
    #/ temp[`int((number/2+1)*width)`-1:`int(number/2*width)`]<=((cnt[`count`-1])?temp[`int(number/2*width-1)`:`int((number/2-1)*width)`]:in[`width`-1:`0`]);
    #/ temp[`int(number/2*width-1)`:`width`]<=temp[`int((number/2-1)*width-1)`:`int(0)`];
    #/ temp[`number*width`-1:`int(number/2+1)*width`]<=temp[`int((number-1)*width-1)`:`int(number/2*width)`];
    #/ end
    #/ assign out[`width`-1:`0`]=temp[`number`*`width`-1:`int((number-1)*width)`];
    #/ assign out[2*`width`-1:`width`]=(cnt[`count`-1])?in[`width`-1:`0`]:temp[`int(number/2*width-1)`:`int((number/2-1)*width)`];
    #/ endmodule
    pass


@convert 
def ModuleType1_switch2(width, N, M):
    #/ module switch2 (
    #/ input clk,
    #/ input cnt,
    #/ input [`2*width`-1:0] in,
    #/ output [`2*width`-1:0] out
    #/ );
    #/ reg [`2*width`-1:0] temp;
    #/ always @(posedge clk)
    #/ begin
    #/ temp[`width`-1:0]<=in[2*`width`-1:`width`];
    #/ temp[`2*width`-1:`width`]<=(cnt)?temp[`width`-1:0]:in[`width`-1:0];
    #/ end
    #/ assign out[`width`-1:`0`]=temp[2*`width`-1:`width`];
    #/ assign out[2*`width`-1:`width`]=(cnt)?in[`width`-1:0]:temp[`width`-1:0];
    #/ endmodule
    pass


# convert to pytv 
@convert
def ModuleType1_counter(N, M, count, value):
    #/ module counter (
    #/ input clk,
    #/ input ctr,
    #/ output reg [`count`-1:0] cnt
    #/ );
    #/ always @(posedge clk)
    #/ begin
    #/ if(ctr)
    #/ cnt <= `value`;
    #/ else
    #/ cnt <= cnt + 1'b1;
    #/ end
    #/ endmodule
    pass

   
# convert to pytv 
@convert
def ModuleType1_early_stop(width, N, M):
    #/ module early_stop (
    #/ input flag,
    #/ input [`N*width`-1:0] in1,
    #/ input [`N*width`-1:0] in2,
    #/ output early_stop
    #/ );
    #/ wire temp;
    #/ assign temp=
    for i in range(1, N):
        #/ ~(in1[`i*width`-1] ^ in2[`i*width`-1]) &
        pass
    #/ ~(in1[`N*width`-1] ^ in2[`N*width`-1]);
    #/ assign early_stop=(flag & temp)?1:0;
    #/ endmodule

  
# convert to pytv 
@convert 
def ModuleType1_early_stop_memory(width, N, M):
    #/ module early_stop_memory (
    #/ input clk,
    #/ input rst,
    #/ input flag,
    #/ input [`N*width`-1:0] in,
    #/ output reg [`N*width`-1:0] out
    #/ );
    #/ always @(posedge clk)
    #/ begin
    #/ if(!rst)
    #/ out<={(`N*width`){1'b0}};
    #/ else if(flag)
    #/ out<=in;
    #/ end
    #/ endmodule
    pass

  
@ convert
def ModuleType1_hard_decision(width, N, M):
    #/ module hard_decision (
    #/ input [`N*width`-1:0] in1,
    #/ input [`N*width`-1:0] in2,
    #/ output [`N-1`:0] out
    #/ );
    #/ wire [`N*width`-1:0] temp;
    for i in range(0,N):
        PORTS_add = {
            'in1': f'in1[{(i+1)*width-1}:{i*width}]',
            'in2': f'in2[{(i+1)*width-1}:{i*width}]',
            'out': f'temp[{(i+1)*width-1}:{i*width}]'
        }
        ModuleAdd(width=width, PORTS=PORTS_add)
    #/ assign out = {
    for i in range(1, N):
        #/ temp[`i*width`-1],
        pass
    #/ temp[`N*width`-1]};
    #/ endmodule


@convert
def ModuleType2_control(width, N, M):
    # 计算中间变量
    t3 = int(math.log(N, 2)) - 1
    m_val = int(math.log((t3 + 1) * int(N / M), 2))
    num_switch = int(math.log(int(N / M), 2))
    t = num_switch + 2 if num_switch < t3 else num_switch
    t2 = int(math.log(t, 2)) if t & (t - 1) == 0 else int(math.log(t, 2)) + 1
    temp1 = sum(2**(num_switch - i) for i in range(num_switch))
    num_state = 2 + t3 * int(N / M) + int(temp1 / 2)
    t4 = int(math.log(num_state, 2))
    t2_minus_1 = t2 - 1
    m_minus_1 = m_val - 1 if m_val > 0 else 0  # 防止负值
    m = m_val

    #/ module control (input clk, input rst,
    #/     output reg [1:0] L_ctr_mux1,
    #/     output reg [`t2_minus_1`:0] L_ctr_mux2,
    #/     output reg [`t2_minus_1`:0] L_ctr_mux3,
    #/     output reg [1:0] R_ctr_mux1,
    #/     output reg [`t2_minus_1`:0] R_ctr_mux2,
    #/     output reg [`t2_minus_1`:0] R_ctr_mux3,
    
    # 动态生成开关输出端口
    for i in range(num_switch):
        #/     output reg L_ctr_switch`i+1`,
        #/     output reg R_ctr_switch`i+1`,
        pass  # 避免空循环语法错误
    
    #/     output reg L_we,
    #/     output reg [`m`:0] L_wr_addr,
    #/     output reg [`m`:0] L_re_addr,
    #/     output reg R_we,
    #/     output reg [`m`:0] R_wr_addr,
    #/     output reg [`m`:0] R_re_addr
    #/ );
    
    # 状态声明
    #/ localparam state_init = 0,
    for i in range(1, num_state - 1):
        #/     state`i` = `i`,
        pass
    #/     state`num_state-1` = `num_state-1`;
    #/ reg [`t4`:0] state;
    #/ always @(posedge clk) begin
    #/     if (!rst) state <= state_init;
    #/     else case (state)
    #/         state_init: begin
    #/             L_ctr_mux1 <= 0;
    #/             L_ctr_mux2 <= 0;
    #/             L_ctr_mux3 <= 0;
    #/             R_ctr_mux1 <= 0;
    #/             R_ctr_mux2 <= 0;
    #/             R_ctr_mux3 <= 0;
    #/             L_we <= 0;
    #/             L_wr_addr <= 0;
    #/             L_re_addr <= 0;
    #/             R_we <= 0;
    #/             R_wr_addr <= 0;
    #/             R_re_addr <= 0;
    
    for i in range(num_switch):
        if i == 0:
            #/             L_ctr_switch1 <= 1;
            #/             R_ctr_switch1 <= 1;
            pass
        else:
            #/             L_ctr_switch`i+1` <= 0;
            #/             R_ctr_switch`i+1` <= 0;
            pass
    
    #/             state <= state1;
    #/         end
    
    # 状态机主体
    if 0 < num_switch < t3:
        temp3 = 0
        for i in range(num_switch):
            temp2 = 2**(num_switch - i)
            for index in range(1, int(N/M) + int(temp2/2) + 1):
                state_num = temp3 + index
                #/         state`state_num`: begin
                if i == 0:
                    #/             L_ctr_mux1 <= 0;
                    #/             R_ctr_mux1 <= 0;
                    pass
                else:
                    #/             L_ctr_mux1 <= 1;
                    #/             R_ctr_mux1 <= 1;
                    pass
                #/             L_ctr_mux2 <= `i`;
                #/             L_ctr_mux3 <= `i`;
                #/             R_ctr_mux2 <= `i`;
                #/             R_ctr_mux3 <= `i`;
                
                if index == int(N/M) + int(temp2/2):
                    for j in range(i+1):
                        #/             L_ctr_switch`j+1` <= 0;
                        #/             R_ctr_switch`j+1` <= 0;
                        pass
                    for j in range(i+1, num_switch):
                        if j == i+1:
                            #/             L_ctr_switch`j+1` <= 1;
                            #/             R_ctr_switch`j+1` <= 1;
                            pass
                        else:
                            #/             L_ctr_switch`j+1` <= 0;
                            #/             R_ctr_switch`j+1` <= 0;
                            pass
                else:
                    for j in range(num_switch):
                        #/             L_ctr_switch`j+1` <= 0;
                        #/             R_ctr_switch`j+1` <= 0;
                        pass
                
                if index < int(temp2/2) + 1:
                    #/             L_we <= 0;
                    #/             L_wr_addr <= 0;
                    #/             R_we <= 0;
                    #/             R_wr_addr <= 0;
                    pass
                else:
                    wr_addr_val = i*int(N/M) + index - int(temp2/2) - 1
                    #/             L_we <= 1;
                    #/             L_wr_addr <= `wr_addr_val`;
                    #/             R_we <= 1;
                    #/             R_wr_addr <= `wr_addr_val`;
                    pass
                
                if index < int(N/M):
                    re_addr_val = i*int(N/M) + index
                    #/             L_re_addr <= `re_addr_val`;
                    #/             R_re_addr <= `re_addr_val`;
                    pass
                elif index == int(N/M) + int(temp2/2):
                    re_addr_val = (i+1)*int(N/M)
                    #/             L_re_addr <= `re_addr_val`;
                    #/             R_re_addr <= `re_addr_val`;
                    pass
                else:
                    #/             L_re_addr <= 0;
                    #/             R_re_addr <= 0;
                    pass
                
                #/             state <= state`state_num+1`;
                #/         end
            temp3 += int(N/M) + int(temp2/2)
        for i in range(num_switch, t3):
            for index in range(1, int(N / M) + 1):
                #/         state`i * int(N / M) + int(temp1 / 2) + index`: begin
                #/             L_ctr_mux1 <= 1;
                #/             R_ctr_mux1 <= 1;
                #/             L_ctr_mux2 <= `num_switch`;
                #/             L_ctr_mux3 <= `num_switch`;
                #/             R_ctr_mux2 <= `num_switch`;
                #/             R_ctr_mux3 <= `num_switch`;
                for j in range(0, num_switch):
                    #/             L_ctr_switch`j+1` <= 0;
                    #/             R_ctr_switch`j+1` <= 0;
                    pass
                if i == t3 - 1:
                    #/             L_we <= 0;
                    #/             L_wr_addr <= 0;
                    #/             R_we <= 0;
                    #/             R_wr_addr <= 0;
                    pass
                else:
                    #/             L_we <= 1;
                    #/             L_wr_addr <= `i * int(N / M) + index - 1`;
                    #/             R_we <= 1;
                    #/             R_wr_addr <= `i * int(N / M) + index - 1`;
                    pass
                if i == t3 - 1 and index == int(N / M):
                    #/             L_re_addr <= 0;
                    #/             R_re_addr <= 0;
                    pass
                else:
                    #/             L_re_addr <= `i * int(N / M) + index`;
                    #/             R_re_addr <= `i * int(N / M) + index`;
                    pass
                #/             state <= state`i * int(N / M) + int(temp1 / 2) + index+1`;
                #/         end
    elif num_switch == 0:
        for index in range(1, t3 + 1):
            #/         state`index`: begin
            if index == 1:
                #/             L_ctr_mux1 <= 0;
                #/             R_ctr_mux1 <= 0;
                pass
            else:
                #/             L_ctr_mux1 <= 1;
                #/             R_ctr_mux1 <= 1;
                pass
            if index < t3:
                #/             L_ctr_mux2 <= 0;
                #/             L_ctr_mux3 <= 0;
                #/             R_ctr_mux2 <= 0;
                #/             R_ctr_mux3 <= 0;
                pass
            else:
                #/             L_ctr_mux2 <= 1;
                #/             L_ctr_mux3 <= 1;
                #/             R_ctr_mux2 <= 1;
                #/             R_ctr_mux3 <= 1;
                pass
            if index < t3:
                #/             L_we <= 1;
                #/             L_wr_addr <= `index - 1`;
                #/             R_we <= 1;
                #/             R_wr_addr <= `index - 1`;
                pass
            else:
                #/             L_we <= 0;
                #/             L_wr_addr <= 0;
                #/             R_we <= 0;
                #/             R_wr_addr <= 0;
                pass
            if index < t3:
                #/             L_re_addr <= `index`;
                #/             R_re_addr <= `index`;
                pass
            else:
                #/             L_re_addr <= `t3-index-1`;
                #/             R_re_addr <= `t3-index-1`;
                pass
                #/             state <= state`index+1`;
            #/         end
    else:
        temp5 = 0
        for i in range(0, num_switch):
            temp2 = int(math.pow(2, num_switch - i))
            for index in range(1, int(N / M) + int(temp2 / 2) + 1):
                #/         state`temp5 + index`: begin
                if i == 0:
                    #/             L_ctr_mux1 <= 0;
                    #/             R_ctr_mux1 <= 0;
                    pass
                else:
                    #/             L_ctr_mux1 <= 1;
                    #/             R_ctr_mux1 <= 1;
                    pass
                #/             L_ctr_mux2 <= `i`;
                #/             L_ctr_mux3 <= `i`;
                #/             R_ctr_mux2 <= `i`;
                #/             R_ctr_mux3 <= `i`;
                if i < num_switch - 1:
                    if index == int(N / M) + int(temp2 / 2):
                        for j in range(0, i + 1):
                            #/             L_ctr_switch`j+1` <= 0;
                            #/             R_ctr_switch`j+1` <= 0;
                            pass
                        for j in range(i + 1, num_switch):
                            if j == i + 1:
                                #/             L_ctr_switch`j+1` <= 1;
                                #/             R_ctr_switch`j+1` <= 1;
                                pass
                            else:
                                #/             L_ctr_switch`j+1` <= 0;
                                #/             R_ctr_switch`j+1` <= 0;
                                pass
                    else:
                        for j in range(0, num_switch):
                            #/             L_ctr_switch`j+1` <= 0;
                            #/             R_ctr_switch`j+1` <= 0;
                            pass
                else:
                    if index == int(N / M) + int(temp2 / 2):
                        for j in range(0, num_switch - 1):
                            #/             L_ctr_switch`j+1` <= 0;
                            #/             R_ctr_switch`j+1` <= 0;
                            pass
                        #/             L_ctr_switch`num_switch` <= 1;
                        #/             R_ctr_switch`num_switch` <= 1;
                    else:
                        for j in range(0, num_switch):
                            #/             L_ctr_switch`j+1` <= 0;
                            #/             R_ctr_switch`j+1` <= 0;
                            pass
                if i == num_switch - 1:
                    #/             L_we <= 0;
                    #/             L_wr_addr <= 0;
                    #/             R_we <= 0;
                    #/             R_wr_addr <= 0;
                    pass
                else:
                    if index < int(temp2 / 2) + 1:
                        #/             L_we <= 0;
                        #/             L_wr_addr <= 0;
                        #/             R_we <= 0;
                        #/             R_wr_addr <= 0;
                        pass
                    else:
                        #/             L_we <= 1;
                        #/             L_wr_addr <= `i * int(N / M) + index - int(temp2 / 2) - 1`;
                        #/             R_we <= 1;
                        #/             R_wr_addr <= `i * int(N / M) + index - int(temp2 / 2) - 1`;
                        pass
                if i == num_switch - 1:
                    if index < int(N / M):
                        #/             L_re_addr <= `i * int(N / M) + index`;
                        #/             R_re_addr <= `i * int(N / M) + index`;
                        pass
                    else:
                        #/             L_re_addr <= 0;
                        #/             R_re_addr <= 0;
                        pass
                else:
                    if index < int(N / M):
                        #/             L_re_addr <= `i * int(N / M) + index`;
                        #/             R_re_addr <= `i * int(N / M) + index`;
                        pass
                    elif index == int(N / M) + int(temp2 / 2):
                        #/             L_re_addr <= (i+1)*int(N/M);
                        #/             R_re_addr <= (i+1)*int(N/M);
                        pass
                    else:
                        #/             L_re_addr <= 0;
                        #/             R_re_addr <= 0;
                        pass
                #/             state <= state`temp5 + index+1`;
                #/         end
            temp5 += int(N / M) + int(temp2 / 2)
    #/ state`1 + t3 * int(N/M) + int(temp1/2)`:
    #/ begin
    #/     L_ctr_mux1 <= 0;
    #/     L_ctr_mux2 <= 0;
    #/     L_ctr_mux3 <= 0;
    for j in range(0, num_switch):
        if j == 0:
            #/             L_ctr_switch`j+1` <= 1;
            #/             R_ctr_switch`j+1` <= 1;
            pass
        else:
            #/             L_ctr_switch`j+1` <= 0;
            #/             R_ctr_switch`j+1` <= 0;
            pass
    #/     L_we <= 0;
    #/     L_wr_addr <= 0;
    #/     L_re_addr <= 0;
    #/     state <= state1;
    #/ end
    
    #/ default: begin
    #/     L_ctr_mux1 <= 0;
    #/     L_ctr_mux2 <= 0;
    #/     L_ctr_mux3 <= 0;
    for j in range(0, num_switch):
        #/     L_ctr_switch`j+1` <= 0;
        pass
    #/     L_we <= 0;
    #/     L_wr_addr <= 0;
    #/     L_re_addr <= 0;
    #/     state <= state_init;
    #/ end
    #/ endcase
    #/ end
    #/ endmodule
    pass


@ convert
def ModuleType2_BCB(algo, N, M, width):
    if algo == 'MS':
        #/ module BCB (
        #/ input [`width`-1:0] up0,
        #/ input [`width`-1:0] up1,
        #/ input [`width`-1:0] down0,
        #/ input [`width`-1:0] down1,
        #/ output [`width`-1:0] out0,
        #/ output [`width`-1:0] out1
        #/ );
        #/ wire sign1,sign2;
        #/ wire [`width`-1:0] temp;
        #/ wire [`width`-1:0] result;
        #/ wire [`width`-2:0] abs1,abs2,abs3;
        #/ wire [`width`-2:0] value1,value2;
        #/ assign sign1=up0[`width`-1] ^ temp[`width`-1];
        #/ assign sign2=up0[`width`-1] ^ down0[`width`-1];
        #/ assign abs1=(up0[`width`-1]==1'b0)?up0[`width`-2:0]:(1'b1+~ up0[`width`-2:0]);
        #/ assign abs2=(temp[`width`-1]==1'b0)?temp[`width`-2:0]:(1'b1+~ temp[`width`-2:0]);
        #/ assign abs3=(down0[`width`-1]==1'b0)?down0[`width`-2:0]:(1'b1+~ down0[`width`-2:0]);
        #/ assign value1=(abs1 < abs2)?abs1:abs2;
        #/ assign value2=(abs1 < abs3)?abs1:abs3;
        #/ assign out0 = (value1)?(sign1)?{sign1,~value1+1'b1}:{sign1,value1}:{(`width`){{1'b0}}};
        #/ assign result = (value2)?(sign2)?{sign2,~value2+1'b1}:{sign2,value2}:{(`width`){{1'b0}}};
        PORTS_add1 = {
        'in1':'up1',
        'in2':'down1',
        'out': 'temp'
        }
        ModuleAdd(width=width, PORTS=PORTS_add1)
        PORTS_add2 = {
        'in1':'up1',
        'in2':'result',
        'out': 'out1'
        }
        ModuleAdd(width=width, PORTS=PORTS_add2)
        #/ endmodule
        pass
    if algo == 'SMS':
        #/ module BCB (
        #/ input [`width`-1:0] up0,
        #/ input [`width`-1:0] up1,
        #/ input [`width`-1:0] down0,
        #/ input [`width`-1:0] down1,
        #/ output [`width`-1:0] out0,
        #/ output [`width`-1:0] out1
        #/ );
        #/ wire sign1,sign2;
        #/ wire [`width`-1:0] temp,temp1,temp2;
        #/ wire [`width`-1:0] result;
        #/ wire [`width`-2:0] abs1,abs2,abs3;
        #/ wire [`width`-2:0] minvalue1,minvalue2;
        #/ wire [`width`-1:0] offset;
        #/ wire [`width`-1:0] offsetvalue1,offsetvalue2;
        #/ wire [`width`-1:0] comvalue1,comvalue2;
        #/ assign offset={`width`{{1'b1}}};
        #/ assign sign1=up0[`width`-1] ^ temp[`width`-1];
        #/ assign sign2=up0[`width`-1] ^ down0[`width`-1];
        #/ assign abs1=(up0[`width`-1]==1'b0)?up0[`width`-2:0]:(1'b1+~ up0[`width`-2:0]);
        #/ assign abs2=(temp[`width`-1]==1'b0)?temp[`width`-2:0]:(1'b1+~ temp[`width`-2:0]);
        #/ assign abs3=(down0[`width`-1]==1'b0)?down0[`width`-2:0]:(1'b1+~ down0[`width`-2:0]);
        #/ assign minvalue1=(abs1 < abs2)?abs1:abs2;
        #/ assign minvalue2=(abs1 < abs3)?abs1:abs3;
        #/ assign temp1={1'b0,minvalue1};
        #/ assign temp2={1'b0,minvalue2};
        #/ assign comvalue1 = (offsetvalue1[`width`-1])?{(`width`){1'b0}}:offsetvalue1;
        #/ assign comvalue2 = (offsetvalue2[`width`-1])?{(`width`){1'b0}}:offsetvalue2;
        #/ assign out0 = (comvalue1)?(sign1)?{sign1,~comvalue1[`width`-2:0]+1'b1}:comvalue1:{(`width`){{1'b0}}};
        #/ assign result = (comvalue2)?(sign2)?{sign2,~comvalue2[`width`-2:0]+1'b1}:comvalue2:{(`width`){{1'b0}}};
        PORTS_add1 = {
        'in1':'up1',
        'in2':'down1',
        'out': 'temp'
        }
        ModuleAdd(width=width, PORTS=PORTS_add1)
        PORTS_add2 = {
        'in1':'temp1',
        'in2':'offset',
        'out': 'offsetvalue1'
        }
        ModuleAdd(width=width, PORTS=PORTS_add2)
        PORTS_add3 = {
        'in1':'temp2',
        'in2':'offset',
        'out': 'offsetvalue2'
        }
        ModuleAdd(width=width, PORTS=PORTS_add3)
        PORTS_add4 = {
        'in1':'up1',
        'in2':'result',
        'out': 'out1'
        }
        ModuleAdd(width=width, PORTS=PORTS_add4)
        #/ endmodule
        pass
    pass


@ convert
def ModuleType2_mux1(width, N, M):
    #/ module mux1 (
    #/ input [1:0] ctr,
    #/ input [`M*width`-1:0] in1,
    #/ input [`M*width`-1:0] in2,
    #/ input [`M*width`-1:0] in3,
    #/ output reg [`M*width`-1:0] out1,
    #/ output reg [`M*width`-1:0] out2
    #/ );
    #/ always @ (*)
    #/ case (ctr)
    #/ 2'b00: begin out1 = in1; out2 = in3; end
    #/ 2'b01: begin out1 = in2; out2 = in3; end
    #/ 2'b10: begin out1 = in2; out2 = in1; end
    #/ default: begin out1 = {(`M*width`){1'b0}};
    #/            out2 = {(`M*width`){1'b0}}; end
    #/ endcase
    #/ endmodule
    pass
    

@ convert
def ModuleType2_mux2(width, N, M):
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
    
    #/ module mux2(
    #/ input [`t1`-1:0] ctr,
    #/ input [`M*width`-1:0] in,
    for i in range(1, t):
        #/ output [`M*width`-1:0] out`i`,
        pass
    #/ output [`M*width`-1:0] out`t`
    #/ );
    for i in range(0, t):
        #/ assign out`i+1` = (ctr == `i`)?in:{(`M*width`){1'b0}};
        pass
    #/ endmodule
    pass
    

@ convert
def ModuleType2_mux3(width, N, M):
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
    #/ module mux3 (
    #/ input [`t1`-1:0] ctr,
    for i in range(1, t + 1):
        #/ input [`M*width`-1:0] in`i`,
        pass
    #/ output reg [`M*width`-1:0] out
    #/ );
    #/ always @ (*)
    #/ case (ctr)
    for i in range(0, t):
        #/ `i`: out = in`i+1`;
        pass
    if t & (t - 1) != 0:
        #/ default: out = {(`M*width`){1'b0}};
        pass
    #/ endcase
    #/ endmodule
    pass
    

@ convert
def ModuleType2_delay_reg(width, N, M):
    #/ module delay_reg (
    #/ input clk,
    #/ input [`M*width`-1:0] in,
    #/ output [`M*width`-1:0] out1,
    #/ output [`N*width`-1:0] out2
    #/ );
    if N == M:
        #/ reg [`M*width`-1:0] temp;
        #/ always @(posedge clk)
        #/ begin
        #/   temp <= in;
        #/ end
        #/ assign out1 = temp;
        #/ assign out2 = temp;
        #/ endmodule
        pass
    else:
        #/ reg [`M*width`-1:0] temp[`int(N/M)-1`:0];
        #/ always @(posedge clk)
        #/ begin
        #/   temp[0] <= in;
        for i in range(1, int(N / M)):
            #/   temp[`i`] <= temp[`i-1`];
            pass
        #/ end
        #/ assign out1 = temp[`int(N/M)-1`];
        #/ assign out2 = {
        for i in range(0, int(N / M) - 1):
            #/   temp[`i`],
            pass
        #/   temp[`int(N/M)-1`]};
        #/ endmodule
    pass
    

@ convert
def ModuleType2_pipe_reg(width, N, M):
    #/ module pipe_reg (
    #/ input clk,
    #/ input [`M*width`-1:0] in,
    #/ output [`M*width`-1:0] out
    #/ );
    #/ reg [`M*width`-1:0] temp;
    #/ always @(posedge clk)
    #/ begin
    #/   temp <= in;
    #/ end
    #/ assign out = temp;
    #/ endmodule
    pass


@ convert
def ModuleType2_memory(width, N, M):
    t = int(math.log(N, 2))
    m = int(math.log(t * int(N / M), 2))
    #/ module memory (
    #/ input clk,
    #/ input rst,
    #/ input L_we,
    #/ input [`m`:0] L_wr_addr,
    #/ input [`m`:0] L_re_addr,
    #/ input R_we,
    #/ input [`m`:0] R_wr_addr,
    #/ input [`m`:0] R_re_addr,
    #/ input [`M*width`-1:0] in1,
    #/ input [`M*width`-1:0] in2,
    #/ output [`M*width`-1:0] out1,
    #/ output [`M*width`-1:0] out2
    #/ );
    #/ reg [`M*width`-1:0] temp[`t*int(N/M)-1`:0];
    #/ always @(posedge clk or negedge rst)
    #/ begin
    #/ if(!rst)
    #/ begin
    for i in range(0, t * int(N / M)):
        #/     temp[`i`] <= {(`M*width`){1'b0}};
        pass
    #/ end
    #/ else
    #/ begin
    #/ if(L_we)
    #/   temp[L_wr_addr] <= in1;
    #/ if(R_we)
    #/   temp[R_wr_addr] <= in2;
    #/ end
    #/ end
    #/ assign out1 = temp[L_re_addr];
    #/ assign out2 = temp[R_re_addr];
    #/ endmodule
    pass


@ convert
def ModuleType2_perm(width, N, M):
    #/ module perm (
    #/ input [`M*width`-1:0] in,
    #/ output [`M*width`-1:0] out
    #/ );
    for i in range(0, M, 2):
        #/ assign out[`i+1`*`width`-1:`i`*`width`] = in[`int(i/2)+1`*`width`-1:`int(i/2)`*`width`];
        #/ assign out[`i+2`*`width`-1:`i+1`*`width`] = in[`int((i+M)/2)+1`*`width`-1:`int((i+M)/2)`*`width`];
        pass
    #/ endmodule
    pass


@ convert
def ModuleType2_reverse_perm(width, N, M):
    #/ module reverse_perm (
    #/ input [`M*width`-1:0] in,
    #/ output [`M*width`-1:0] out
    #/ );
    for i in range(0, M, 2):
        #/ assign out[`int(i/2)+1`*`width`-1:`int(i/2)`*`width`] = in[`i+1`*`width`-1:`i`*`width`];
        #/ assign out[`int((i+M)/2)+1`*`width`-1:`int((i+M)/2)`*`width`] = in[`i+2`*`width`-1:`i+1`*`width`];
        pass
    #/ endmodule
    pass


@ convert
def ModuleType2_gen_bcb(width, N, M, algo):
    #/ module gen_BCB (
    #/ input [`M*width`-1:0] up,
    #/ input [`M*width`-1:0] down,
    #/ output [`M*width`-1:0] out
    #/ );
    for i in range(0, int(M / 2)):
        PORTS_bcb = {
            "up0": f"up[{i*2+1}*{width}-1:{i*2}*{width}]",
            "up1": f"up[{i*2+2}*{width}-1:{i*2+1}*{width}]",
            "down0": f"down[{i*2+1}*{width}-1:{i*2}*{width}]",
            "down1": f"down[{i*2+2}*{width}-1:{i*2+1}*{width}]",
            "out0": f"out[{i*2+1}*{width}-1:{i*2}*{width}]",
            "out1": f"out[{i*2+2}*{width}-1:{i*2+1}*{width}]"
        }
        ModuleType2_BCB(width=width, algo=algo, N=N, M=M, PORTS=PORTS_bcb)
        pass
    #/ endmodule
    pass


@ convert
def ModuleType2_gen_switch(width, N, M, number):
    t = int(math.log(number, 2))
    count = t
    #/ module gen_switch (
    #/ input clk,
    #/ input ctr,
    #/ input [`M*width`-1:0] in,
    #/ output [`M*width`-1:0] out
    #/ );
    #/ wire [`count`-1:0] cnt;
    PORTS_counter = {
        'clk': 'clk',
        'ctr': 'ctr',
        'cnt': 'cnt'
    }
    value = 0
    ModuleType2_counter(N=N, M=M, count=count, value=value, PORTS=PORTS_counter)
    for i in range(0, int(M / 2), 1):
        PORTS_switch = {
            'clk': 'clk',
            'cnt': 'cnt',
            'in': f'in[{(i+1)*width-1}:{i*width}]',
            'out': f'out[{(i+1)*width-1}:{i*width}]'
        }
        ModuleType2_switch(width=width,N=N,M=M,number=number,count=count,PORTS=PORTS_switch)
        pass
    #/ endmodule
    pass


@ convert
def ModuleType2_gen_switch2(width, N, M, count):
    #/ module gen_switch2 (
    #/ input clk,
    #/ input ctr,
    #/ input [`M*width`-1:0] in,
    #/ output [`M*width`-1:0] out
    #/ );
    #/ wire cnt;
    PORTS_counter = {
        'clk': 'clk',
        'ctr': 'ctr',
        'cnt': 'cnt'
    }
    value = 0
    ModuleType2_counter(N=N, M=M, count=count, value=value, PORTS=PORTS_counter)
    for i in range(0, int(M / 2), 1):
        PORTS_switch = {
            'clk': 'clk',
            'cnt': 'cnt',
            'in': f'in[{(i+1)*width-1}:{i*width}]',
            'out': f'out[{(i+1)*width-1}:{i*width}]'
        }
        ModuleType2_switch2(width=width,N=N,M=M,PORTS=PORTS_switch)
        pass
        pass
    #/ endmodule
    pass


@ convert
def ModuleType2_switch(width, N, M, number, count):
    t = int(math.log(number, 2))
    count = t
    #/ module switch (
    #/ input clk,
    #/ input [`count`-1:0] cnt,
    #/ input [`2*width`-1:0] in,
    #/ output [`2*width`-1:0] out
    #/ );
    #/ reg [`number*width`-1:0] temp;
    #/ always @(posedge clk)
    #/ begin
    #/ temp[`width`-1:0] <= in[`2*width`-1:`width`];
    #/ temp[`(number/2+1)`*`width`-1:`number/2`*`width`] <= (cnt[`count`-1])?temp[`number/2`*`width`-1:`(number/2-1)`*`width`]:in[`width`-1:0];
    #/ temp[`number/2`*`width`-1:`width`] <= temp[`(number/2-1)`*`width`-1:0];
    #/ temp[`number*width`-1:`(number/2+1)`*`width`] <= temp[`(number-1)`*`width`-1:`number/2`*`width`];
    #/ end
    #/ assign out[`width`-1:0] = temp[`number*width`-1:`(number-1)`*`width`];
    #/ assign out[`2*width`-1:`width`] = (cnt[`count`-1])?in[`width`-1:0]:temp[`number/2`*`width`-1:`(number/2-1)`*`width`];
    #/ endmodule
    pass


@ convert
def ModuleType2_switch2(width, N, M):
    #/ module switch2 (
    #/ input clk,
    #/ input cnt,
    #/ input [`2*width`-1:0] in,
    #/ output [`2*width`-1:0] out
    #/ );
    #/ reg [`2*width`-1:0] temp;
    #/ always @(posedge clk)
    #/ begin
    #/ temp[`width`-1:0] <= in[`2*width`-1:`width`];
    #/ temp[`2*width`-1:`width`] <= (cnt)?temp[`width`-1:0]:in[`width`-1:0];
    #/ end
    #/ assign out[`width`-1:0] = temp[`2*width`-1:`width`];
    #/ assign out[`2*width`-1:`width`] = (cnt)?in[`width`-1:0]:temp[`width`-1:0];
    #/ endmodule
    pass


@ convert
def ModuleType2_counter(N, M, count, value):
    #/ module counter (
    #/ input clk,
    #/ input ctr,
    #/ output reg [`count`-1:0] cnt
    #/ );
    #/ always @(posedge clk)
    #/ begin
    #/ if(ctr)
    #/ cnt <= `value`;
    #/ else
    #/ cnt <= cnt + 1'b1;
    #/ end
    #/ endmodule
    pass


@ convert
def ModuleType2_G_matrix(width, N, M):
    n = int(math.log(N, 2))
    #/ module G_matrix (
    #/ input [`N*width`-1:0] in1,
    #/ input [`N*width`-1:0] in2,
    #/ input [`N*width`-1:0] in3,
    #/ input [`N*width`-1:0] in4,
    #/ output stop,
    #/ output [`N`-1:0] out
    #/ );
    #/ wire [`N`-1:0] temp1,temp2;
    for i in range(0, (n - 1) * 2 + 1):
        #/ wire [`N`-1:0] data`i`;
        pass
    PORTS_hard_decision1 = {
        'in1': 'in1',
        'in2': 'in2',
        'out': 'temp1'
    }
    ModuleType2_hard_decision(width=width, N=N, M=M, PORTS=PORTS_hard_decision1)
    PORTS_hard_decision2 = {
        'in1': 'in3',
        'in2': 'in4',
        'out': 'temp2'
    }
    ModuleType2_hard_decision(width=width, N=N, M=M, PORTS=PORTS_hard_decision2)
    PORTS_xor_pass = {
        'in': 'temp1',
        'out': 'data0'
    }
    ModuleType2_xor_pass(width=width, N=N, M=M, PORTS=PORTS_xor_pass)
    for i in range(1, n):
        PORTS_shuffle = {
            'in': f'data{(i-1)*2}',
            'out': f'data{(i-1)*2+1}'
        }
        ModuleType2_shuffle(width=width, N=N, M=M, PORTS=PORTS_shuffle)
        PORTS_xor_pass = {
            'in': f'data{(i-1)*2+1}',
            'out': f'data{i*2}'
        }
        ModuleType2_xor_pass(width=width, N=N, M=M, PORTS=PORTS_xor_pass)
        pass
    #/ assign stop=(temp2==data`(n-1)*2`)?1:0; 
    #/ assign out=temp1;
    #/ endmodule
    pass


@ convert
def ModuleType2_xor_pass(width, N, M):
    #/ module xor_pass (
    #/ input [`N`-1:0] in,
    #/ output [`N`-1:0] out
    #/ );
    for i in range(0, N, 2):
        #/ xor x`i` (out[`i`],in[`i`],in[`i+1`]);
        #/ assign out[`i+1`]=in[`i+1`];
        pass
    #/ endmodule
    pass


@ convert
def ModuleType2_shuffle(width, N, M):
    #/ module shuffle (
    #/ input [`N`-1:0] in,
    #/ output [`N`-1:0] out
    #/ );
    for i in range(0, int(N / 2)):
        #/ assign out[`i*2`]=in[`i`];
        #/ assign out[`i*2+1`]=in[`i+int(N/2)`];
        pass
    #/ endmodule
    pass


@ convert
def ModuleType2_hard_decision(width, N, M):
    #/ module hard_decision (
    #/ input [`N*width`-1:0] in1,
    #/ input [`N*width`-1:0] in2,
    #/ output [`N`-1:0] out
    #/ );
    #/ wire [`N*width`-1:0] temp;
    for i in range(0, N):
        PORTS_exm = {
            'in1': f'in1[{(i+1)*width-1}:{i*width}]',
            'in2': f'in2[{(i+1)*width-1}:{i*width}]',
            'out': f'temp[{(i+1)*width-1}:{i*width}]'
        }
        ModuleAdd(width=width, PORTS=PORTS_exm)
        pass
    #/ assign out = {
    for i in range(1, N):
        #/ temp[`i*width`-1],
        pass
    #/ temp[`N*width`-1]};
    #/ endmodule
    pass


@ convert   
def Moduletop(archi, algo, N, M, width):
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
        #/module top (
        #/input clk,
        #/input rst,
        #/input [`N*width`-1:0] fully_llr_R,
        #/input [`M*width`-1:0] semi_llr_R,
        #/input [`M*width`-1:0] semi_llr_L,
        #/output out_valid,
        #/output [`N`-1:0] dec);
        #/wire [`M*width`-1:0] mux1_out1,mux1_out2,mux3_out;
        for i in range(0, t):
            #/ wire [`M*width`-1:0] mux2_out`i+1`;
            pass
        for i in range(0, num_switch):
            #/ wire [`M*width`-1:0] switch_out`i+1`;
            pass
        #/ wire [`M*width`-1:0] perm_out,reverse_perm_out;
        #/ wire [`M*width`-1:0] gen_BCB_out,delay_reg_out,mem_out;
        #/ wire [`N*width`-1:0] series_parallel_out,early_stop_mem_out;
        #/ wire early_stop,flag;
        #/ wire [1:0] ctr_mux1;
        #/ wire [`t2-1`:0] ctr_mux2;
        #/ wire [`t2-1`:0] ctr_mux3;
        #/ wire we;
        #/ wire [`m-1`:0] wr_addr;
        #/ wire [`m-1`:0] re_addr;
        pass
    
        for i in range(0, num_switch):
            #/ wire ctr_switch`i+1`;
            pass
        
        PORTS_mux1 = {
        'ctr': 'ctr_mux1',
        'in1': 'semi_llr_R',
        'in2': 'semi_llr_L',
        'in3': 'mem_out',
        'in4': 'delay_reg_out',
        'out1': 'mux1_out1',
        'out2': 'mux1_out2'
        }
        ModuleType1_mux1(width=width, N=N, M=M, PORTS=PORTS_mux1)
       
        PORTS_gen_BCB = {
        'up': 'mux1_out1',
        'down': 'mux1_out2',
        'out': 'gen_BCB_out'
        }
        ModuleType1_gen_bcb(width=width, N=N, M=M, algo=algo, PORTS=PORTS_gen_BCB)
        
        PORTS_mux2 = {
        'ctr': 'ctr_mux2',
        'in': 'gen_BCB_out',
        }
        for i in range(1, t):
            PORTS_mux2['out%d' % i] = 'mux2_out%d' % i
        PORTS_mux2['out%d' % t] = 'mux2_out%d' % t
        ModuleType1_mux2(width=width, N=N, M=M, PORTS=PORTS_mux2)
        
        PORTS_perm = {
        'in':'mux2_out1',
        'out': 'perm_out'
        }
        ModuleType1_perm(width=width, N=N, M=M, PORTS=PORTS_perm)
        
        PORTS_reverse_perm = {
        'in':'mux2_out2',
        'out':'reverse_perm_out'
        }
        ModuleType1_reverse_perm(width=width, N=N, M=M, PORTS=PORTS_reverse_perm)    
        if N > M:
            for i in range(0, num_switch - 1):
                temp1 = int(math.pow(2, num_switch - i))
                temp2 = int(math.log(temp1, 2))
                PORTS_gen_switch = {
                    'clk': 'clk',
                    'ctr': 'ctr_switch%d' % (i + 1),
                    'in' : f"mux2_out{i+3}",
                    'out': f"switch_out{i+1}"
                }
                ModuleType1_gen_switch(width=width, M=M, N=N, number=temp1, count=temp2, PORTS=PORTS_gen_switch)
            PORTS_gen_switch2 = {
                'clk': 'clk',
                'ctr': 'ctr_switch%d' % num_switch,
                'in' : f"mux2_out{num_switch+2}",
                'out': f"switch_out{num_switch}"
            }
            ModuleType1_gen_switch2(width=width, M=M, N=N, PORTS=PORTS_gen_switch2)

        PORTS_mux3 = {
        'ctr': 'ctr_mux3',
        'in1': 'perm_out',
        'in2':'reverse_perm_out',
        }
        for i in range(0, num_switch):
            PORTS_mux3['in%d' % (i + 3)] = f'switch_out{i+1}'
        PORTS_mux3['in%d' % (num_switch + 3)] = f"mux2_out{num_switch+3}"
        PORTS_mux3['out'] = 'mux3_out'
        ModuleType1_mux3(width=width, N=N, M=M, PORTS=PORTS_mux3)
        
        PORTS_delay_reg = {
        'clk': 'clk',
        'in': 'mux3_out',
        'out1': 'delay_reg_out',
        'out2': 'series_parallel_out'
        }
        ModuleType1_delay_reg(width=width, N=N, M=M, PORTS=PORTS_delay_reg)
    
        PORTS_memory = {
        'clk': 'clk',
        'rst': 'rst',
        'we': 'we',
        'wr_addr': 'wr_addr',
        're_addr':'re_addr',
        'in': 'mux3_out',
        'out': 'mem_out'
        }
        ModuleType1_memory(width=width, N=N, M=M, PORTS=PORTS_memory)
        
        PORTS_control = {
        'clk': 'clk',
        'rst': 'rst',
        'early_stop': 'early_stop',
        'ctr_mux1': 'ctr_mux1',
        'ctr_mux2': 'ctr_mux2',
        'ctr_mux3': 'ctr_mux3',
        'we': 'we',
        'wr_addr': 'wr_addr',
        're_addr':'re_addr',
        'flag': 'flag',
        'out_valid': 'out_valid'}
        for i in range(0, num_switch):
            PORTS_control['ctr_switch%d' % (i + 1)] = 'ctr_switch%d' % (i + 1)
        ModuleType1_control(width=width, N=N, M=M, PORTS=PORTS_control)
        PORTS_early_stop = {
        'flag': 'flag',
        'in1':'series_parallel_out',
        'in2': 'early_stop_mem_out',
        'early_stop': 'early_stop'
        }
        ModuleType1_early_stop(width=width, N=N, M=M, PORTS=PORTS_early_stop)
        
        PORTS_early_stop_memory = {
        'clk': 'clk',
        'rst': 'rst',
        'flag': 'flag',
        'in': 'series_parallel_out',
        'out': 'early_stop_mem_out'
        }
        ModuleType1_early_stop_memory(width=width, N=N, M=M, PORTS=PORTS_early_stop_memory)
        
        PORTS_hard_decision = {
        'in1': 'fully_llr_R',
        'in2':'series_parallel_out',
        'out': 'dec'
        }
        ModuleType1_hard_decision(width=width, N=N, M=M, PORTS=PORTS_hard_decision)
        #/ endmodule
    if archi == 'TypeII':
        t1 = int(math.log(N, 2)) - 1
        m = int(math.log((t1 + 1) * int(N / M), 2))
        num_switch = int(math.log(int(N / M), 2))
        if num_switch < t1:
            t = num_switch + 2
        else:
            t = num_switch
        count = t
        if t & (t - 1) == 0:
            t2 = int(math.log(t, 2))
        else:
            t2 = int(math.log(t, 2)) + 1
        #/ module top (
        #/ input clk,
        #/ input rst,
        #/ input [`N*width`-1:0] fully_llr_R,
        #/ input [`N*width`-1:0] fully_llr_L,
        #/ input [`M*width`-1:0] semi_llr_R,
        #/ input [`M*width`-1:0] semi_llr_L,
        #/ output out_valid,
        #/ output [`N`-1:0] dec
        #/ );
        #/ wire [`M*width`-1:0] L_mux1_out1,L_mux1_out2,R_mux1_out1,R_mux1_out2,L_mux3_out,R_mux3_out;
        
        for i in range(0, t):
            #/ wire [`M*width`-1:0] L_mux2_out`i+1`;
            #/ wire [`M*width`-1:0] R_mux2_out`i+1`;
            pass
        for i in range(0, num_switch):
            #/ wire [`M*width`-1:0] L_switch_out`i+1`;
            #/ wire [`M*width`-1:0] R_switch_out`i+1`;
            pass
        if num_switch < t1:
            #/ wire [`M*width`-1:0] L_perm_out,L_reverse_perm_out,R_perm_out,R_reverse_perm_out;
            pass
    
        #/ wire [`M*width`-1:0] L_gen_BCB_out,L_delay_reg_out,R_gen_BCB_out,R_delay_reg_out;
        #/ wire [`M*width`-1:0] L_pipe_reg_out,R_pipe_reg_out,L_mem_out,R_mem_out;
        #/ wire [`N*width`-1:0] L_series_parallel_out,R_series_parallel_out;
        #/ wire [1:0] L_ctr_mux1;
        #/ wire [1:0] R_ctr_mux1;
        #/ wire [`t2`-1:0] L_ctr_mux2;
        #/ wire [`t2`-1:0] L_ctr_mux3;
        #/ wire [`t2`-1:0] R_ctr_mux2;
        #/ wire [`t2`-1:0] R_ctr_mux3;
        #/ wire L_we;
        #/ wire [`m`:0] L_wr_addr;
        #/ wire [`m`:0] L_re_addr;
        #/ wire R_we;
        #/ wire [`m`:0] R_wr_addr;
        #/ wire [`m`:0] R_re_addr;

        for i in range(0, num_switch):
            #/ wire L_ctr_switch`i+1`;
            #/ wire R_ctr_switch`i+1`;
            pass

        PORTS_mux1 = {
            'ctr': 'L_ctr_mux1',
            'in1': 'semi_llr_R',
            'in2': 'L_delay_reg_out',
            'in3': 'L_pipe_reg_out',
            'out1': 'L_mux1_out1',
            'out2': 'L_mux1_out2'
        }
        ModuleType2_mux1(width=width, N=N, M=M, PORTS=PORTS_mux1)
        
        PORTS_gen_BCB_L = {
            'up': 'L_mux1_out1',
            'down': 'L_mux1_out2',
            'out': 'L_gen_BCB_out'
        }
        ModuleType2_gen_bcb(width=width, N=N, M=M, algo=algo, PORTS=PORTS_gen_BCB_L)
        
        PORTS_mux2_L = {
            'ctr': 'L_ctr_mux2',
            'in': 'L_gen_BCB_out',
        }
        for i in range(1, t):
            PORTS_mux2_L['out%d' % i] = 'L_mux2_out%d' % i
        PORTS_mux2_L['out%d' % t] = 'L_mux2_out%d' % t
        ModuleType2_mux2(width=width, N=N, M=M, PORTS=PORTS_mux2_L)

        if N > M:
            for i in range(0, num_switch - 1):
                temp1 = int(math.pow(2, num_switch - i))
                temp2 = int(math.log(temp1, 2))
                PORTS_gen_switch_L = {
                    'clk': 'clk',
                    'ctr': f'L_ctr_switch{i + 1}',
                    'in': f'L_mux2_out{i + 1}',
                    'out': f'L_switch_out{i + 1}'
                }
                ModuleType2_gen_switch(width=width, M=M, N=temp1, number=temp2, PORTS=PORTS_gen_switch_L)
            PORTS_gen_switch2_L = {
                'clk': 'clk',
                'ctr': f'L_ctr_switch{num_switch}',
                'in': f'L_mux2_out{num_switch}',
                'out': f'L_switch_out{num_switch}'
            }
            ModuleType2_gen_switch2(width=width, M=M, N=N, count=count, PORTS=PORTS_gen_switch2_L)
    
        if num_switch < t1:
            PORTS_perm_L = {
                'in': f'L_mux2_out{t - 1}',
                'out': 'L_perm_out'
            }
            ModuleType2_perm(width=width, N=N, M=M, PORTS=PORTS_perm_L)
            PORTS_reverse_perm_L = {
                'in': f'L_mux2_out{t}',
                'out': 'L_reverse_perm_out'
            }
            ModuleType2_reverse_perm(width=width, N=N, M=M, PORTS=PORTS_reverse_perm_L)

        PORTS_mux3_L = {
            'ctr': 'L_ctr_mux3',
        }
        for i in range(0, num_switch):
            PORTS_mux3_L[f'in{i + 1}'] = f'L_switch_out{i + 1}'
        if num_switch < t1:
            PORTS_mux3_L['in%d' % (t - 1)] = 'L_perm_out'
            PORTS_mux3_L['in%d' % t] = 'L_reverse_perm_out'
            PORTS_mux3_L['out'] = 'L_mux3_out'
        else:
            PORTS_mux3_L['out'] = 'L_mux3_out'
        ModuleType2_mux3(width=width, N=N, M=M, PORTS=PORTS_mux3_L)

        PORTS_delay_reg_L = {
            'clk': 'clk',
            'in': 'L_mux3_out',
            'out1': 'L_delay_reg_out',
            'out2': 'L_series_parallel_out'
        }
        ModuleType2_delay_reg(width=width, N=N, M=M, PORTS=PORTS_delay_reg_L)

        PORTS_mux1_R = {
            'ctr': 'R_ctr_mux1',
            'in1': 'semi_llr_L',
            'in2': 'R_delay_reg_out',
            'in3': 'R_pipe_reg_out',
            'out1': 'R_mux1_out1',
            'out2': 'R_mux1_out2'
        }
        ModuleType2_mux1(width=width, N=N, M=M, PORTS=PORTS_mux1_R)
        
        PORTS_gen_BCB_R = {
            'up': 'R_mux1_out1',
            'down': 'R_mux1_out2',
            'out': 'R_gen_BCB_out'
        }
        ModuleType2_gen_bcb(width=width, N=N, M=M, algo=algo, PORTS=PORTS_gen_BCB_R)
        
        PORTS_mux2_R = {
            'ctr': 'R_ctr_mux2',
            'in': 'R_gen_BCB_out',
        }
        for i in range(1, t):
            PORTS_mux2_R[f'out{i}'] = f'R_mux2_out{i}'
        PORTS_mux2_R[f'out{t}'] = f'R_mux2_out{t}'
        ModuleType2_mux2(width=width, N=N, M=M, PORTS=PORTS_mux2_R)

        if N > M:
            for i in range(0, num_switch - 1):
                temp1 = int(math.pow(2, num_switch - i))
                temp2 = int(math.log(temp1, 2))
                PORTS_gen_switch_R = {
                    'clk': 'clk',
                    'ctr': f'R_ctr_switch{i + 1}',
                    'in': f'R_mux2_out{i + 1}',
                    'out': f'R_switch_out{i + 1}'
                }
                ModuleType2_gen_switch(width=width, M=M, N=temp1, number=temp2, PORTS=PORTS_gen_switch_R)
            PORTS_gen_switch2_R = {
                'clk': 'clk',
                'ctr': f'R_ctr_switch{num_switch}',
                'in': f'R_mux2_out{num_switch}',
                'out': f'R_switch_out{num_switch}'
            }
            ModuleType2_gen_switch2(width=width, M=M, N=N, count=count, PORTS=PORTS_gen_switch2_R)
    
        if num_switch < t1:
            PORTS_perm_R = {
                'in': f'R_mux2_out{t - 1}',
                'out': 'R_perm_out'
            }
            ModuleType2_perm(width=width, N=N, M=M, PORTS=PORTS_perm_R)
            PORTS_reverse_perm_R = {
                'in': f'R_mux2_out{t}',
                'out': 'R_reverse_perm_out'
            }
            ModuleType2_reverse_perm(width=width, N=N, M=M, PORTS=PORTS_reverse_perm_R)

        PORTS_mux3_R = {
            'ctr': 'R_ctr_mux3',
        }
        for i in range(0, num_switch):
            PORTS_mux3_R[f'in{i + 1}'] = f'R_switch_out{i + 1}'
        if num_switch < t1:
            PORTS_mux3_R['in%d' % (t - 1)] = 'R_perm_out'
            PORTS_mux3_R['in%d' % t] = 'R_reverse_perm_out'
            PORTS_mux3_R['out'] = 'R_mux3_out'
        else:
            PORTS_mux3_R['out'] = 'R_mux3_out'
        ModuleType2_mux3(width=width, N=N, M=M, PORTS=PORTS_mux3_R)
        
        PORTS_delay_reg_R = {
            'clk': 'clk',
            'in': 'R_mux3_out',
            'out1': 'R_delay_reg_out',
            'out2': 'R_series_parallel_out'
        }
        ModuleType2_delay_reg(width=width, N=N, M=M, PORTS=PORTS_delay_reg_R)
        
        PORTS_memory = {
            'clk': 'clk',
            'rst': 'rst',
            'L_we': 'L_we',
            'L_wr_addr': 'L_wr_addr',
            'L_re_addr': 'L_re_addr',
            'R_we': 'R_we',
            'R_wr_addr': 'R_wr_addr',
            'R_re_addr': 'R_re_addr',
            'in1': 'L_delay_reg_out',
            'in2': 'R_delay_reg_out',
            'out1': 'L_mem_out',
            'out2': 'R_mem_out'
        }
        ModuleType2_memory(width=width, N=N, M=M, PORTS=PORTS_memory)
        
        PORTS_pipe_reg_L = {
            'clk': 'clk',
            'in': 'L_mem_out',
            'out': 'L_pipe_reg_out'
        }
        ModuleType2_pipe_reg(width=width, N=N, M=M, PORTS=PORTS_pipe_reg_L)
        
        PORTS_pipe_reg_R = {
            'clk': 'clk',
            'in': 'R_mem_out',
            'out': 'R_pipe_reg_out'
        }
        ModuleType2_pipe_reg(width=width, N=N, M=M, PORTS=PORTS_pipe_reg_R)
        
        PORTS_control = {
            'clk': 'clk',
            'rst': 'rst',
            'L_ctr_mux1': 'L_ctr_mux1',
            'L_ctr_mux2': 'L_ctr_mux2',
            'L_ctr_mux3': 'L_ctr_mux3',
            'R_ctr_mux1': 'R_ctr_mux1',
            'R_ctr_mux2': 'R_ctr_mux2',
            'R_ctr_mux3': 'R_ctr_mux3',
        }
        for i in range(0, num_switch):
            PORTS_control[f'L_ctr_switch{i + 1}'] = f'L_ctr_switch{i + 1}'
            PORTS_control[f'R_ctr_switch{i + 1}'] = f'R_ctr_switch{i + 1}'
        PORTS_control['L_we'] = 'L_we'
        PORTS_control['L_wr_addr'] = 'L_wr_addr'
        PORTS_control['L_re_addr'] = 'L_re_addr'
        PORTS_control['R_we'] = 'R_we'
        PORTS_control['R_wr_addr'] = 'R_wr_addr'
        PORTS_control['R_re_addr'] = 'R_re_addr'
        ModuleType2_control(width=width, N=N, M=M, PORTS=PORTS_control)
        
        PORTS_G_matrix = {
            'in1': 'fully_llr_R',
            'in2': 'L_series_parallel_out',
            'in3': 'fully_llr_L',
            'in4': 'R_series_parallel_out',
            'stop': 'out_valid',
            'out': 'dec'
        }
        ModuleType2_G_matrix(width=width, N=N, M=M, PORTS=PORTS_G_matrix) 
        #/ endmodule

@ convert
def Moduletest(width, N, M, archi, algo, int_width, frac_width, code_rate=0.5, clock_period_ns=20.0, root_path=str(), testcase_name="BP decoder", relative_io_paths=False):
    #/ `timescale 1ns / 1ps
    #/ module test;
    #/ reg clk;
    #/ reg rst;
    #/ reg [`N*width`-1:0] fully_llr_R;
    if archi == 'TypeII':
        #/ reg [`N*width`-1:0] fully_llr_L;
        pass
    #/ reg [`M*width`-1:0] semi_llr_R; // both lines are previously N
    #/ reg [`M*width`-1:0] semi_llr_L;
    #/ wire [`N`-1:0] dec;
    #/ wire out_valid;
    #/ integer cycle_count;
    #/ integer latency_cycles;
    #/ integer latency_file;
    #/ reg latency_reported;

    # top exam(.clk(clk),.rst(rst),.fully_llr_R(fully_llr_R),.semi_llr_R(semi_llr_R),.semi_llr_L(semi_llr_L),.dec(dec),.out_valid(out_valid));
    ports_top = {
        'clk': 'clk',
        'rst': 'rst',
        'fully_llr_R': 'fully_llr_R',
        'semi_llr_R':'semi_llr_R',
        'semi_llr_L':'semi_llr_L',
        'dec':'dec',
        'out_valid':'out_valid'
    }
    if archi == 'TypeII':
        ports_top['fully_llr_L'] = 'fully_llr_L'
    Moduletop(archi=archi, algo=algo, N=N, M=M, PORTS=ports_top, width=width)
    clk_period = float(clock_period_ns)
    if clk_period <= 0:
        raise ValueError(f"clock_period_ns must be positive, got {clk_period}")
    clk_period_half = clk_period / 2.0
    #/ initial
    #/ begin
    #/     clk = 1'b0;
    #/     rst = 1'b0;
    #/     cycle_count = 0;
    #/     latency_cycles = 0;
    #/     latency_reported = 0;
    #/     #`clk_period`
    #/     rst = 1'b1;
    #/ end

    #/ always
    #/ begin
    #/     #`clk_period_half`
    #/     clk = ~clk;
    #/ end
    # read from input file
    # In case when N==M , only one round of input dump is required
    generation_input_file_dir = os.path.abspath(
        os.path.join(root_path, "input_files")
    )
    if relative_io_paths:
        # Paths emitted into Verilog are relative to the isolated simulation cwd.
        input_file_dir = "input_files"
        output_file_dir = "output_files"
        output_file_path = "output_files/decoding_output.txt"
        latency_output_path = "output_files/latency_output.txt"
    else:
        input_file_dir = generation_input_file_dir.replace("\\", "/")
        output_file_dir = os.path.abspath(os.path.join(root_path, 'output_files')).replace("\\", "/")
        output_file_path = os.path.abspath(os.path.join(output_file_dir, 'decoding_output.txt')).replace("\\", "/")
        latency_output_path = os.path.abspath(os.path.join(output_file_dir, 'latency_output.txt')).replace("\\", "/")
    k_info_tmp = round(float(code_rate) * N)
    file_suffix = f"N{N}K{k_info_tmp}INTDWT{int_width}FRACDWT{frac_width}MS.txt"
    if N == M:
        #/ initial begin
        #/ // #500 $stop;
        #/ end
        #/ integer i, file, ret;
        #/ reg temp;
        #/ initial
        #/ begin
        #/     file=$fopen("`os.path.join(input_file_dir, f"R{file_suffix}")`","r");
        #/     for(i=0;i<(`N*width`);i=i+1) begin
        #/         ret = $fscanf(file,"%b",temp);
        #/         fully_llr_R[`N*width`-1-i] = temp;
        #/     end
        #/     $fclose(file);
        if archi == 'TypeII':
            #/     file=$fopen("`os.path.join(input_file_dir, f"L{file_suffix}")`","r");
            #/     for(i=0;i<(`N*width`);i=i+1) begin
            #/         ret = $fscanf(file,"%b",temp);
            #/         fully_llr_L[`N*width`-1-i] = temp;
            #/     end
            #/     $fclose(file);
            pass
        #/     file=$fopen("`os.path.join(input_file_dir, f"R{file_suffix}")`","r");
        #/     for(i=0;i<(`N*width`);i=i+1) begin
        #/         ret = $fscanf(file,"%b",temp);
        #/         semi_llr_R[`N*width`-1-i] = temp;
        #/     end
        #/     $fclose(file);
        #/     file=$fopen("`os.path.join(input_file_dir, f"L{file_suffix}")`","r");
        #/     for(i=0;i<(`N*width`);i=i+1) begin
        #/         ret = $fscanf(file,"%b",temp);
        #/         semi_llr_L[`N*width`-1-i] = temp;
        #/     end
        #/     $fclose(file);
        #/ end
        pass
    # In case when N>M, repetitive input dump is required
    elif N > M:
        num_decoding_states = 2* (int(N/M))*int(math.log2(N))-1#638 # (N=1024, M=32)
        initial_delay = clk_period + clk_period_half
        in_state_delay = clk_period
        in_iteration_delay = clk_period * num_decoding_states
        # in_R_L_delay = int((in_iteration_delay-60)/2) # ok
        in_R_L_delay = 0  # 320 for (N=32,M=16)
        # if N == (2*M):
        #     in_R_L_delay = int((in_iteration_delay-3*clk_period)/2)
        # elif N == (4*M):
        #     in_R_L_delay = int((in_iteration_delay-7*clk_period)/2)
        # elif N == (8*M):
        #     in_R_L_delay = int((in_iteration_delay-15*clk_period)/2)
        N_over_M = int(N/M)
        log2_N_over_M_1 = int(math.log2(N_over_M))+1
        n_temp_period = int(math.pow(2, log2_N_over_M_1)) - 1
        in_R_L_delay = int((in_iteration_delay-n_temp_period*clk_period)/2)
        
        # in_R_L_delay = 120#clk_period * int(N/M) * 2 # 120, 16; 80, 8 seems correct
        num_iter = 100
        input_file_path_R = os.path.join(generation_input_file_dir, f"R{file_suffix}")
        input_file_path_L = os.path.join(generation_input_file_dir, f"L{file_suffix}")
        R_= []
        L = []
        with open(input_file_path_R, 'r') as f_R:
             R = f_R.read().split('\n')
        with open(input_file_path_L, 'r') as f_L:
             L = f_L.read().split('\n')
        input_group_len = int(M*width)
        total_len = int(N*width)
        num_input_group = int(N/M)
        fully_llr_R = ''.join(R)
        fully_llr_L = ''.join(L)
        semi_llr_R = []
        semi_llr_L = []
        for i in range (0, num_input_group):
            R_slice = ''.join(R[i*input_group_len:(i+1)*input_group_len])
            L_slice = ''.join(L[i*input_group_len:(i+1)*input_group_len])
            semi_llr_R.append(R_slice)
            semi_llr_L.append(L_slice)
        # reverse semi_llr_R and semi_llr_L
        semi_llr_R = semi_llr_R[::-1]
        semi_llr_L = semi_llr_L[::-1]
        R_delay_list = [0] * (num_input_group + 1)
        L_delay_list = [0] * (num_input_group + 1)
        for k in range(0, num_input_group):
            if k==0: 
                R_delay_list[k] = initial_delay 
            else:
                R_delay_list[k] = R_delay_list[k-1] + in_state_delay 
        for k in range(0, num_input_group):
            if k==0: 
                L_delay_list[k] = R_delay_list[num_input_group-1] + in_R_L_delay 
            else:
                L_delay_list[k] = L_delay_list[k-1] + in_state_delay 
        #/ integer k, i, file;
        #/ // Initialization of L and R
        #/ initial
        #/ begin
        #/     fully_llr_R = `total_len`'b`fully_llr_R`;
        if archi == 'TypeII':
            #/     fully_llr_L = `total_len`'b`fully_llr_L`;
            pass
        for k in range(0, num_input_group):
            if k==0:
                #/     #`initial_delay`  semi_llr_R = `input_group_len`'b`semi_llr_R[k]`;
                pass
            else:
                #/     #`in_state_delay`  semi_llr_R = `input_group_len`'b`semi_llr_R[k]`;
                pass
        for k in range(0, num_input_group):
            if k==0:
                #/     #`in_R_L_delay`  semi_llr_L = `input_group_len`'b`semi_llr_L[k]`;
                pass
            else:
                #/     #`in_state_delay`  semi_llr_L = `input_group_len`'b`semi_llr_L[k]`;
                pass
        #/ end
        #/ // Assign R and L in each iteration
        for k in range(0, num_input_group):
            #/ initial
            #/ begin
            #/     #`R_delay_list[k]`  
            #/     for (k=1; k<`num_iter`; k=k+1)
            #/     #`in_iteration_delay`  semi_llr_R = `input_group_len`'b`semi_llr_R[k]`;
            #/ end
            pass
        for k in range(0, num_input_group):
            #/ initial
            #/ begin
            #/     #`L_delay_list[k]`  
            #/     for (k=1; k<`num_iter`; k=k+1)
            #/     #`in_iteration_delay`  semi_llr_L = `input_group_len`'b`semi_llr_L[k]`;
            #/ end
            pass
        pass
    #/ always @(posedge clk or negedge rst)
    #/ begin
    #/     if(!rst)
    #/     begin
    #/         cycle_count <= 0;
    #/         latency_reported <= 0;
    #/     end
    #/     else if(!latency_reported)
    #/     begin
    #/         if(out_valid==1'b1)
    #/         begin
    #/             latency_cycles = cycle_count;
    #/             latency_reported <= 1;
    #/             latency_file=$fopen("`latency_output_path`","w");
    #/             $fwrite(latency_file,"%0d\\n",latency_cycles);
    #/             $fclose(latency_file);
    #/             $display("Success. The latency of `testcase_name` is %0d cycles.", latency_cycles);
    #/         end
    #/         cycle_count <= cycle_count + 1;
    #/     end
    #/ end
    #/ always @(posedge clk) 
    #/ begin
    #/     if(out_valid==1'b1)
    #/     begin
    #/         #`clk_period_half`
    #/         file=$fopen("`output_file_path`","w");
    #/         for(i=0;i<`N`;i=i+1)
    #/             $fwrite(file,"%d\\n",dec[`N`-1-i]);
    #/         $fwrite(file,"\\n");
    #/         $fclose(file);
    #/         $stop; 
    #/     end
    #/     //if (out_valid==1'b1)
    #/     //begin
    #/     //    #60
    #/     //    //$stop;
    #/     //end
    #/ end
    #/ initial begin
    #/     $dumpfile("wave.vcd");
    #/     $dumpvars(0,test0000000001);
    #/     // #6000  $finish;
    #/ end
    #/ endmodule
    pass
    
    
    




# Moduletop(archi=archi, algo=algo, N=N, M=M)
