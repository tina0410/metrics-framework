import numpy as np
import matplotlib.pyplot as plt

# 原始数据
data_str = """
16	75.9
17	80.6
18	85.4
19	90.2
20	94.9
21	99.7
22	104.4
23	109.2
24	114
25	118.7
"""

# 解析数据
lines = data_str.strip().split('\n')
x = np.array([float(line.split()[0]) for line in lines])
y = np.array([float(line.split()[1]) for line in lines])

# 定义拟合函数
def fit_func(p, x):
    a, b = p
    return a * x + b

# 使用 numpy.polyfit 进行线性拟合 (1次多项式)
# params[0] 是 a (斜率), params[1] 是 b (截距)
params = np.polyfit(x, y, 1)
a, b = params

print(f"拟合函数为: y = a*x + b")
print(f"拟合参数 a (斜率): {a}")
print(f"拟合参数 b (截距): {b}")

# (可选) 绘制拟合结果图
plt.figure(figsize=(10, 6))
plt.scatter(x, y, label='Original Data')
plt.plot(x, fit_func(params, x), color='red', label='Fitted Line')
plt.title('Linear Fit')
plt.xlabel('x')
plt.ylabel('y')
plt.legend()
plt.grid(True)
plt.show()