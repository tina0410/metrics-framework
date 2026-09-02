import ast
from typing import Dict, Tuple
import sympy
import numpy as np

def get_dependency_matrices(code: str) -> Dict[str, Tuple[np.ndarray, list[str]]]:
    """
    Parses the given code containing perfectly nested loops and computes dependency
    matrices for variables accessed within the loops.

    Parameters:
    - code: A string containing the Python code with nested loops.

    Returns:
    - dependency_matrices: A dictionary mapping variable names to tuples of their
      dependency matrices and the global loop variables.
    """
    class LoopVisitor(ast.NodeVisitor):
        def __init__(self):
            self.loop_vars_order = []  # Global order of loop variables
            self.loop_vars_set = set()
            self.accessed_vars = {}  # Store variable accesses with coefficients

        def visit_For(self, node):
            # Get the loop variable name
            if isinstance(node.target, ast.Name):
                loop_var = node.target.id
                if loop_var not in self.loop_vars_set:
                    self.loop_vars_set.add(loop_var)
                    self.loop_vars_order.append(loop_var)
            self.generic_visit(node)

        def visit_Subscript(self, node):
            # Handle array indexing
            if isinstance(node.value, ast.Name):
                var_name = node.value.id
                indices = self.get_indices(node.slice)
                if var_name not in self.accessed_vars:
                    self.accessed_vars[var_name] = []
                self.accessed_vars[var_name].append(indices)
            self.generic_visit(node)

        def get_indices(self, node):
            # Extract indices from subscript nodes
            if isinstance(node, ast.Index):
                return [self.extract_coefficients(node.value)]
            elif isinstance(node, ast.Tuple):
                indices = []
                for elt in node.elts:
                    indices.append(self.extract_coefficients(elt))
                return indices
            else:
                return []

        def extract_coefficients(self, node):
            code_str = ast.unparse(node)
            # Declare loop variables as SymPy symbols
            loop_symbols = {var: sympy.Symbol(var) for var in self.loop_vars_order}
            expr = sympy.sympify(code_str, locals=loop_symbols, evaluate=False)
            coeffs = {}
            for var in self.loop_vars_order:
                sym_var = loop_symbols[var]
                coeff = expr.coeff(sym_var)
                coeffs[var] = int(coeff) if coeff != 0 else 0
            return coeffs

    # Parse the code into an AST
    tree = ast.parse(code)
    visitor = LoopVisitor()
    visitor.visit(tree)

    # Build dependency matrices for each accessed variable
    dependency_matrices = {}
    global_loop_vars = visitor.loop_vars_order
    num_vars = len(global_loop_vars)
    for var_name, indices_list in visitor.accessed_vars.items():
        # Initialize the dependency matrix
        # Number of rows equals number of indices per access
        num_indices = len(indices_list[0])  # Assuming consistent indexing
        matrix = np.zeros((num_indices, num_vars), dtype=int)

        # Since all accesses are expected to have the same number of indices,
        # we can process one set of indices per variable
        index_coeffs_list = indices_list[0]
        for row_idx, index_coeffs in enumerate(index_coeffs_list):
            for col_idx, loop_var in enumerate(global_loop_vars):
                coeff = index_coeffs.get(loop_var, 0)
                matrix[row_idx, col_idx] = coeff

        # Remove rows where all coefficients are zero
        non_zero_rows = ~np.all(matrix == 0, axis=1)
        reduced_matrix = matrix[non_zero_rows, :]

        dependency_matrices[var_name] = (reduced_matrix, global_loop_vars)
    return dependency_matrices
    
def extract_variables_in_order(code_str, exclude_builtins=True, exclude_loop_vars=True):
    """
    按代码执行顺序提取变量名，排除内置函数和循环变量
    
    参数:
        code_str (str): 要分析的代码字符串
        exclude_builtins (bool): 是否排除内置函数（如range, len等）
        exclude_loop_vars (bool): 是否排除循环变量（如for i中的i）
    
    返回:
        list: 按变量首次出现顺序排列的变量名列表
    """
    try:
        tree = ast.parse(code_str)
    except SyntaxError:
        raise ValueError("输入的代码字符串不是有效的Python语法")

    variables = []
    seen_vars = set()
    builtins = set(dir(__builtins__)) if exclude_builtins else set()
    builtins.add("range")  # 确保 range 被排除
    loop_vars = set()

    # 先收集循环变量（如 for i in range(3) 中的 i）
    if exclude_loop_vars:
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                loop_vars.add(node.target.id)

    # 使用 NodeVisitor 按代码顺序遍历
    class VariableVisitor(ast.NodeVisitor):
        def visit_Name(self, node):
            var_name = node.id
            if (var_name not in seen_vars and 
                var_name not in builtins and 
                var_name not in loop_vars):
                variables.append(var_name)
                seen_vars.add(var_name)
        
        def visit_Subscript(self, node):
            if isinstance(node.value, ast.Name):
                var_name = node.value.id
                if (var_name not in seen_vars and 
                    var_name not in builtins and 
                    var_name not in loop_vars):
                    variables.append(var_name)
                    seen_vars.add(var_name)
            self.generic_visit(node)  # 继续遍历子节点

    visitor = VariableVisitor()
    visitor.visit(tree)

    return variables
# Example usage:
if __name__ == "__main__":
    code = """
for i in range(10):
    for j in range(10 - i):
        for k in range(10 - j):
            G[i, j] += H[i,k] * HH[k, j]
"""

    dependency_matrices = get_dependency_matrices(code)
    global_loop_vars = dependency_matrices[next(iter(dependency_matrices))][1]
    print("Global Loop Variables:", global_loop_vars)

    for var_name, (matrix, loop_vars) in dependency_matrices.items():
        print(f"\nVariable {var_name} Dependency Matrix:")
        print(matrix)
