from basic_support import generate, simulate
from modules.Counter import ModuleCounter
from BehavModel_Counter import step


def run(params, tmp_path):
    top = generate(ModuleCounter, params, tmp_path)
    width = params['DWT']
    reset, clear, wrap = (params[k] for k in ('IF_RST_N','HAS_CLEAR','HAS_WRAP'))
    ports = ['.clk(clk)', '.enable(enable)', '.count(count)']
    if reset:
        ports.append('.rst_n(rst_n)')
    if clear:
        ports.append('.clear(clear)')
    if wrap:
        ports.append('.wrap(wrap)')
    lines = ['module tb;', 'reg clk=0, rst_n=1, enable=0, clear=0;',
             f'wire [{width-1}:0] count; wire wrap;',
             top+' dut('+','.join(ports)+');', 'initial begin']
    if reset:
        lines += ['#1; rst_n=0; #1; if (count !== 0) $fatal(1,"reset count");', 'rst_n=1;']
        if wrap:
            lines += ['if (wrap !== 0) $fatal(1,"reset wrap");']
    elif clear:
        lines += ['clear=1; #5; clk=1; #1; clk=0; clear=0;']
    else:
        # No reset and no clear gives an uninitialized hardware register.
        # Check that contract, then deposit a value only for transition tests.
        lines += ["#1; if ((^count) !== 1'bx) $fatal(1,\"expected unknown initial state\");", 'dut.count=0;']
    count = 0
    for i in range(80):
        en, clr = int(i % 7 != 0), int(i in (3,7,19,20,49,63))
        if reset and i == 40:
            lines += ['#1; rst_n=0; #1; if (count !== 0) $fatal(1,"midstream async reset");', 'rst_n=1;']
            if wrap:
                lines += ['if (wrap !== 0) $fatal(1,"midstream wrap reset");']
            count = 0
        count, expected_wrap = step(count,en,clr,width,params['STEP'],clear,wrap)
        lines += [f'enable={en}; clear={clr}; #5; clk=1; #1;',
                  f'if (count !== {width}\'d{count}) $fatal(1,"cycle {i} count=%h",count);']
        if wrap:
            lines += [f'if (wrap !== 1\'b{expected_wrap}) $fatal(1,"cycle {i} wrap");']
        lines += ['clk=0; #1;']
    lines += ['$display("PASS"); $finish; end endmodule']
    simulate(tmp_path, '\n'.join(lines))
