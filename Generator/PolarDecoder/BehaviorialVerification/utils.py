import os
import subprocess
import pytv
import shutil
from pytv import convert
from pytv import moduleloader


def run_iverilog_flow(folder_path, capture_output=False, raise_errors=False):
    """Compile BP_tb.v and run the original wave/wave.vcd simulation flow."""
    target_dir = folder_path
    current_dir = os.getcwd()
    run_kwargs = {
        "check": True,
        "text": True,
        "stdout": subprocess.PIPE if capture_output else None,
        "stderr": subprocess.STDOUT if capture_output else None,
    }
    try:
        os.chdir(target_dir)
        print(f"切换到目录: {os.getcwd()}")
        print("正在编译...")
        compiled = subprocess.run(
            ["iverilog", "-o", "wave", "BP_tb.v"], **run_kwargs
        )
        print("正在仿真...")
        simulated = subprocess.run(
            ["vvp", "-n", "wave", "-lxt2"], **run_kwargs
        )
        if capture_output:
            return (compiled.stdout or "") + (simulated.stdout or "")
        return ""
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        print(f"仿真命令失败: {error}")
        if raise_errors:
            raise
    finally:
        os.chdir(current_dir)
    return ""


# def run_cpp_flow():
#     subprocess.run("./run.sh")
#     subprocess.run("./3")
#     pass
    
    
def run_cpp_flow(command, cwd_in):
    '''
    Executes a command and raises an error if it fails.
    Captures and prints the standard error output on failure.
    Returns the standard output on success.
    '''
    try:
        result = subprocess.run(
            command,
            cwd = cwd_in,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            text = True,
            check = True,
            shell = True
        )
        return result.stdout
    except subprocess.CalledProcessError as error:
        print(f"\033[31mError: \033[0m{error.stderr}")
        raise error

def merge_files(
    folder_path,
    output_filename,
    exclude_files=None,
    suffix=None,
    sort_files=False,
):
    """Merge files, with optional filters for simulation assembly."""
    excluded = set(exclude_files or ())
    file_list = [
        filename
        for filename in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, filename))
        and filename != output_filename
        and filename not in excluded
        and (suffix is None or filename.endswith(suffix))
    ]
    if sort_files:
        file_list.sort()

    with open(
        os.path.join(folder_path, output_filename), "w", errors="ignore"
    ) as outfile:
        for filename in file_list:
            file_path = os.path.join(folder_path, filename)
            with open(file_path, "r", errors="ignore") as infile:
                outfile.write(f"// === Contents from: {filename} ===\n")
                outfile.write(infile.read())
                outfile.write("\n\n")

def delete_file(filename):
    os.remove(filename)
    
def move_and_rename_file(source_dir, target_dir, old_filename, new_filename):
    '''
    Used in test_xxx.py to move and rename files.
    '''
    source_file_path = os.path.join(source_dir, old_filename)
    target_file_path = os.path.join(target_dir, new_filename)
    try:
        shutil.move(source_file_path, target_file_path)
        print(f"Moving {old_filename} to {target_dir} and renaming it as {new_filename}")
    except FileNotFoundError:
        print(f"File {old_filename} not found in {source_dir}")
    except Exception as e:
        print(f"Error in Moving {old_filename} to {target_dir} and renaming it as {new_filename} : {e}")

                
                
def bin_file_to_hex(filename):
    with open(filename, 'r') as file:
        lines = file.readlines()
    
    # 移除每行的换行符并组合成二进制字符串
    bin_str = ''.join(line.strip() for line in lines)
    
    # 计算需要补零的位数（使总长度成为4的倍数）
    padding = 4 - len(bin_str) % 4
    if padding != 4:  # 如果长度不是4的倍数，在前面补零
        bin_str = '0' * padding + bin_str
    
    # 每4位一组转换为十六进制
    hex_chars = []
    for i in range(0, len(bin_str), 4):
        group = bin_str[i:i+4]
        hex_digit = hex(int(group, 2))[2:]  # 去掉hex()返回的'0x'前缀
        hex_chars.append(hex_digit)
    
    return ''.join(hex_chars)
    
    
def merge_2_files(folder_path, file_name_1, file_name_2, output_filename):
    file_list = [file_name_1, file_name_2]
    with open(os.path.join(folder_path, output_filename), 'w', errors='ignore') as outfile:
        for filename in file_list:
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r', errors='ignore') as infile:
                outfile.write(f"// === Contents from: {filename} ===\n")
                outfile.write(infile.read())
                outfile.write("\n\n")  # 添加两个换行作为文件分隔符
                
    
                
                
# @ convert
# def Moduledump(dump_file_path, N, dump_port, file_handle='file', integer_iter='i', temp_reg='temp', integer_return='ret'):
#     #/ file = $fopen(`dump_file_path`,"r");
#     #/ for(`integer_iter`=0;i<`N`;`integer_iter`=`integer_iter`+1) begin
#     #/     `integer_return` = $fscanf(`file`,"%b",`temp_reg`);
#     #/     
#     #/ end
#     pass