import numpy as np
import ast
from itertools import product
from typing import List, Tuple
def generate_pe_addresses_and_times(T, iteration_vectors, computation_duration=1):
    pe_addresses = []
    spatial_coords = []

    print("iteration_vectors",iteration_vectors)
    for I in iteration_vectors:
        I = np.array(I)
        S = T.dot(I)
        spatial_coord = S[:-1]
        time = S[-1]
        spatial_coords.append(spatial_coord)
        pe_addresses.append({
            'iteration': tuple(I),
            'PE_address': spatial_coord,
            'time': time
        })
     
    spatial_coords_array = np.array(spatial_coords)
    
    #min_coords = spatial_coords_array.min(axis=0)
    #offsets = 1 - min_coords
    
    pe_times = {}

    for entry in pe_addresses:
        spatial_coord = entry['PE_address']
        adjusted_coord = spatial_coord# + offsets
        adjusted_coord = adjusted_coord.astype(int)
        pe_address = tuple(adjusted_coord)

        time = entry['time']
        start_time = time
        end_time = time

        if pe_address not in pe_times:
            pe_times[pe_address] = {'start_time': start_time, 'end_time': end_time}
        else:
            pe_times[pe_address]['start_time'] = min(pe_times[pe_address]['start_time'], start_time)
            pe_times[pe_address]['end_time'] = max(pe_times[pe_address]['end_time'], end_time)

    unique_pe_addresses = set(pe_times.keys())

    return unique_pe_addresses, pe_times

def get_edge_points_with_times(points, vector, pe_times=None):
    # Normalize the vector
    vector = np.array(vector, dtype=float)
    vector_norm = np.linalg.norm(vector)
    if vector_norm == 0:
        raise ValueError("The direction vector cannot be zero.")
    vector = vector / vector_norm  # Unit vector in the direction

    # Get the orthogonal vector for 2D case
    orthogonal_vector = np.array([-vector[1], vector[0]])
    orthogonal_vector = orthogonal_vector / np.linalg.norm(orthogonal_vector)

    # Dictionary to hold the minimum point along the vector for each projection
    projection_dict = {}
    for point in points:
        point_array = np.array(point, dtype=float)
        # Project point onto the orthogonal vector
        projection_orth = np.dot(point_array, orthogonal_vector)
        # Round the projection to handle floating-point precision
        projection_orth = round(projection_orth, 6)
        # Project point onto the given vector
        projection_vector = np.dot(point_array, vector)
        # If this projection is not in the dictionary or if it's closer along the vector, update it
        if projection_orth not in projection_dict or projection_vector < projection_dict[projection_orth]['projection_vector']:
            projection_dict[projection_orth] = {
                'point': point,
                'projection_vector': projection_vector
            }
       
    # Extract the points from the dictionary
    edge_points = [value['point'] for value in projection_dict.values()]
    # Sort the edge points for consistent output
    edge_points.sort()

    # Get times for edge points
    edge_times = {}
    if pe_times is not None:
        for point in edge_points:
            if point in pe_times:
                edge_times[point] = pe_times[point]
            else:
                edge_times[point] = {'start_time': None, 'end_time': None}
    else:
        edge_times = {point: {'start_time': None, 'end_time': None} for point in edge_points}

    return edge_points, edge_times

def extract_iterations(code_str: str) -> List[Tuple[int, ...]]:
    """
    准确提取嵌套循环的迭代向量
    
    参数:
        code_str: 包含for循环的代码字符串
        
    返回:
        包含所有迭代向量的列表，如 [(0,0), (0,1), ...]
        保证同一维度的循环结果不会混合
    """
    try:
        tree = ast.parse(code_str)
    except (SyntaxError, IndentationError):
        return []

    loops = []  # 存储各层循环的range对象
    results = []  # 存储最终结果

    def visit(node):
        nonlocal loops, results
        
        if isinstance(node, ast.For):
            # 提取循环变量
            if not isinstance(node.target, ast.Name):
                return
            
            # 解析range参数
            if (isinstance(node.iter, ast.Call) and
                isinstance(node.iter.func, ast.Name) and
                node.iter.func.id == 'range'):
                
                args = []
                for arg in node.iter.args:
                    if isinstance(arg, ast.Constant):
                        args.append(arg.value)
                    else:
                        return  # 跳过含变量的range
                
                # 创建range对象
                if len(args) == 1:
                    current_range = range(args[0])
                elif len(args) == 2:
                    current_range = range(args[0], args[1])
                elif len(args) == 3:
                    current_range = range(args[0], args[1], args[2])
                else:
                    return
                
                loops.append(current_range)
                
                # 检查是否是内层循环
                has_nested = any(isinstance(n, ast.For) for n in node.body)
                if not has_nested:
                    # 只添加完整嵌套循环的结果
                    if len(loops) > 1:  # 确保是嵌套循环
                        results.extend(product(*loops))
                
                # 继续遍历子节点
                for child in node.body:
                    visit(child)
                
                loops.pop()  # 回溯

    # 遍历AST
    for node in ast.walk(tree):
        visit(node)

    return results