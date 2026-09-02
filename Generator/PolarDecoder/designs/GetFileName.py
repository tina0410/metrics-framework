import os

def get_verilog_files_string(directory, base_dir=""):
    """
    获取指定目录下所有.v文件名，并按照格式进行输出，包含完整路径
    
    参数:
    directory: 要查找的目录
    base_dir: 基础目录，用于构建相对路径
    
    返回:
    格式化的字符串，如 {./RTL/RnFFT_Batch/Radix2_Points90/Config1/file1.v, ...}
    """
    # 查找目录中的所有.v文件
    verilog_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.v'):
                # 获取完整路径
                full_path = os.path.join(root, file)
                
                # 如果提供了base_dir，则计算相对于base_dir的路径
                if base_dir:
                    rel_path = os.path.relpath(full_path, base_dir)
                else:
                    # 否则使用完整路径
                    rel_path = full_path
                
                # 将反斜杠转换为正斜杠
                rel_path = rel_path.replace('\\', '/')
                
                # # 添加 ./ 前缀
                if not rel_path.startswith('./'):
                    rel_path = './' + rel_path
                
                verilog_files.append(rel_path)
    
    # 按字母顺序排序
    verilog_files.sort()
    
    # 格式化输出
    if verilog_files:
        formatted_string = "{" + " ".join(verilog_files) + "}"
        return formatted_string
    else:
        return "{}"
        
if __name__ == "__main__":
    print(get_verilog_files_string("./RTL", base_dir="./RTL"))  # Example usage, adjust the directory as needed