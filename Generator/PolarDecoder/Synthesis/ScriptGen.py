import os
import sys
import glob
import shutil

class synthesis:
    filename = "dc.tcl"
    topname = "top"
    period = 5 # ns
    
    def __init__(self, filename="dc.tcl", topname="top", period=5):
        self.filename = filename
        self.topname = topname
        self.period = period
        
    def GenFileList(self, filelist_path="./"):
        # Scan the the folder ./RTL for all the .v files and write them to filelist.f
        # The filelist.f file will be used by the synthesis tool to compile the design
        # Get the current working directory
        current_dir = os.getcwd()
        # Get the path to the designs folder
        designs_dir = os.path.join(current_dir, "RTL")
        # Get the path to the filelist.f file (local to this script)
        filelist_path = os.path.join(current_dir, filelist_path, "filelist.f")
        # Check if the filelist.f file already exists
        if os.path.exists(filelist_path):
            # If it exists, delete it
            os.remove(filelist_path)
        # Create a new filelist.f file
        with open(filelist_path, "w") as filelist:
            # Scan the designs folder for all .v files and sort them alphabetically
            files = sorted(glob.glob(os.path.join(designs_dir, "**", "*.v"), recursive=True))
            for file in files:
                # Convert absolute path to relative path with ./RTL/ prefix
                rel_path = os.path.relpath(file, os.path.join(current_dir))
                # Format as ./RTL/filename.v
                formatted_path = "./{}".format(rel_path)
                # Write the relative file path to the filelist.f file
                filelist.write(formatted_path + "\n")
    
    def genscript(self):
        with open(self.filename, 'w') as f:
            f.write("# DC script\n")
            f.write("set_host_options -max_cores 16\n")
            
            f.write("# 1. Import and elaborate Verilog files\n")
            f.write("analyze -format verilog -vcs \"-f ./filelist.f\"\n")
            f.write(f"elaborate {self.topname}\n")
            f.write(f"current_design {self.topname}\n")
            f.write("link\n")
            f.write("check_design\n")
            
            f.write("# 2. Setting synthesis parameters\n")
            f.write(f"create_clock -period {self.period} -name clk [get_ports clk]\n")
            f.write("set_dont_touch_network [get_clocks clk]\n")
            f.write("set_fix_hold [get_clocks clk]\n")
            f.write("set_clock_uncertainty 0.00000000001 [get_clocks clk]\n")
            f.write("set_clock_latency 0.00000000001 [get_clocks clk]\n")
            f.write("set_ideal_network [get_ports clk]\n")
            f.write("set_input_delay -max 0.00000000001 -clock clk [remove_from_collection [all_inputs] [get_port clk]]\n")
            f.write("set_output_delay -max 0.000000000001 -clock clk [all_outputs]\n")
            # f.write("set_app_var verilog_no_tri true\n")
            # f.write("set_app_var verilogout_equation false\n")
            f.write("remove_unconnected_ports -blast_buses [get_cells -hierarchical *]\n")
            
            f.write("# 3. Compile the design\n")
            f.write("compile_ultra\n")
            # f.write(f"compile -exact_map -map_effort high -area_effort high -power_effort high -boundary_optimization\n")
            f.write("optimize_registers\n")
            f.write(f"write -f ddc -hier -out {self.topname}.ddc\n")
            # f.write("remove_design *\n")
            # f.write(f"read_ddc {self.topname}.ddc\n")
            f.write("link\n")
            
            f.write("# 4. Report design to file\n")
            f.write(f"set report_filename {self.topname}.txt\n")
            f.write("uplevel #0 { report_design } >> $report_filename\n")
            f.write("uplevel #0 { report_reference } >> $report_filename\n")
            f.write("uplevel #0 { report_power -analysis_effort low } >> $report_filename\n")
            f.write("uplevel #0 { report_timing -path full -delay max -nworst 5 -max_paths 10 -significant_digits 2 -sort_by group } >> $report_filename\n")
            f.write("exit\n")
            pass   

if __name__ == "__main__":
    top = synthesis(filename="./scripts/dc_top.tcl", topname="top0000000001", period=2.5)
    top.GenFileList(filelist_path="./scripts/")
    top.genscript()