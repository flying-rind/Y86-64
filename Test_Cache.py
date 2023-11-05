"""
Test_Cache.py
=============
这个程序生成采用分块和不采用分块的矩阵乘法的地址访问序列
将地址访问序列输入到Cache中进行测试,以计算命中率,
模拟的矩阵乘法代码为:
```
for i in range(N):
    for j in range(N):
        for k in range(N):
            r += y[i][k] * z[k][j]
    x[i][j] = r
```
我们假设三个矩阵都是int类型,在主存中连续存放,x放在前64*64*4的位置
y紧随x,z紧随y
"""
import Resources
import numpy as np

Address_Access_Seq = []
# 矩阵规模
N = 64
# x、y、z矩阵的起始物理地址（字节寻址）
x_address_start = 0
y_address_start = N*N*8
z_address_start = N*N*8*2

# 给定访问的数组名称和行列下标,计算其对应的主存物理地址的起始地址（字节寻址）
def Calc_Physical_Address(Matrix_Name:str, line_no:int, column_no:int):
    global x_address_start,y_address_start, z_address_start
    address_start = eval(Matrix_Name + '_address_start')
    physical_address = address_start + line_no*4*N + column_no*4
    # debug
    # print(physical_address)

    return physical_address

# 模拟矩阵乘过程,生成地址访问序列
for i in range(N):
    for j in range(N):
        for k in range(N):
            # y[i][k]
            entry = {}
            entry['Operation'] = 'Read'
            entry['Address'] = Calc_Physical_Address('y', i, k)
            # debug
            # print(Calc_Physical_Address('y', i, k))
            Address_Access_Seq.append(entry)


            # z[k][j]
            entry = {}
            entry['Operation'] = 'Read'
            entry['Address'] = Calc_Physical_Address('z', k, j)
            Address_Access_Seq.append(entry)

    # x[i][j]
    entry = {}
    entry['Operation'] = 'Write'
    entry['Address'] = Calc_Physical_Address('x', i, j)
    Address_Access_Seq.append(entry)

Access_Time = len(Address_Access_Seq)
print("Total access Cache times:", Access_Time)

# 接下来以生成的地址序列访问Cache
DCache = Resources.Data_Cache()
schedule = 0
for entry in Address_Access_Seq:
    op = entry['Operation']
    addr = entry['Address']
    if op == 'Read':
        DCache.Read_Cache(np.uint16(addr))
    else:
        DCache.Write_Cache(np.uint16(addr), '11')
    schedule += 1
    if schedule %1000 == 0:
        print("Current progress %f" %(schedule / Access_Time))

# 释放Cache
DCache.Release()