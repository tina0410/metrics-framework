# DC script
set_host_options -max_cores 16
# 1. Import and elaborate Verilog files
analyze -format verilog -vcs "-f ./filelist.f"
elaborate top0000000001
current_design top0000000001
link
check_design
# 2. Setting synthesis parameters
create_clock -period 2.5 -name clk [get_ports clk]
set_dont_touch_network [get_clocks clk]
set_fix_hold [get_clocks clk]
set_clock_uncertainty 0.00000000001 [get_clocks clk]
set_clock_latency 0.00000000001 [get_clocks clk]
set_ideal_network [get_ports clk]
set_input_delay -max 0.00000000001 -clock clk [remove_from_collection [all_inputs] [get_port clk]]
set_output_delay -max 0.000000000001 -clock clk [all_outputs]
remove_unconnected_ports -blast_buses [get_cells -hierarchical *]
# 3. Compile the design
compile_ultra
optimize_registers
write -f ddc -hier -out top0000000001.ddc
link
# 4. Report design to file
set report_filename top0000000001.txt
uplevel #0 { report_design } >> $report_filename
uplevel #0 { report_reference } >> $report_filename
uplevel #0 { report_power -analysis_effort low } >> $report_filename
uplevel #0 { report_timing -path full -delay max -nworst 5 -max_paths 10 -significant_digits 2 -sort_by group } >> $report_filename
exit
