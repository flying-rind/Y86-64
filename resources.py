'''
Resources.py
这个py文件中包含了CPU中的各个资源部件的定义和实现，包括了：
1. 寄存器和状态码
2. 主存
3. Cache
'''

import math
import random
import numpy as np

Max_Memory = 65536

# 主存大小为65536,内存地址为16位
Dmem = np.full(Max_Memory, "00")      
Imem = np.full(Max_Memory, "00")      

# 设置寄存器初值
reg = [0]*16        # 16通用寄存器, 15表示空寄存器
reg[4] = 500        # %rsp初值为500
PC = 0              # pc寄存器
stat = 1            # 程序状态
ZF = SF = OF =0     # 条件码

OP = {
    0:'+',
    1:'-',
    2:'&',
    3:'^',
    4:'*',
    5:'//'
}

'''
为主存增加一级Cache
采用组相联,替换策略为随机替换
写Cache时采用写回,写不命中时采用写分配
'''
class Cache:
    # Cache的总大小
    CACHE_SIZE = 4096
    # 统计总访问次数
    Access_Times_Count = 0
    # 统计失效次数
    Miss_Times_Count = 0
    
    '''
    Cache默认为2路组相联,块大小为16
    Cache将Data_Cache(字节为单位,每个单元存放长度为2的字符串)和Tag_Cache(每个单元存放一个int型)分离
    '''
    def __init__(self, BLOCK_SIZE:int = 8, ASSOCIATIVITY:int = 2):
        self.BLOCK_SIZE = BLOCK_SIZE
        self.ASSOCIATIVITY = ASSOCIATIVITY
        # 组数和组索引需要的位数
        Groups = self.CACHE_SIZE//BLOCK_SIZE//ASSOCIATIVITY
        self.Group_Index_Bits = int(math.log(Groups, 2))
        # 块偏移需要的位数
        self.Block_Offset_Bits = int(math.log(self.BLOCK_SIZE, 2))
        # 标记需要的位数
        self.Tag_Bits = 16 - self.Block_Offset_Bits - self.Group_Index_Bits

        # 分配DataCache(每行包含一个valid位和dirty位)和TagCache
        self.Data_Cache = np.full((Groups, ASSOCIATIVITY, BLOCK_SIZE+2), "00")
        self.Tag_Cache = np.full((Groups, ASSOCIATIVITY), 0, dtype = int)

        # print(self.Data_Cache)

    '''
    给定一个地址,返回地址拆分后得到的
    (Tag, Group_Index, Block_Offset)
    (int, int, int)
    '''
    def Split_Address(self, address:np.int16):
        # 计算块偏移
        mask = (1<<self.Block_Offset_Bits) - 1
        Block_Offset = address & mask

        address >>= self.Block_Offset_Bits

        # 计算组索引
        mask = (1<<self.Group_Index_Bits) - 1
        Group_Index = address & mask

        address >>= self.Group_Index_Bits

        # 计算Tag
        mask = (1<<self.Tag_Bits) - 1
        Tag = address & mask

        return (Tag, Group_Index, Block_Offset)
    
    '''
    给定地址,读取Cache,返回读取到的一个字节(长度为2的字符串)
    访问时更新访问总次数和失效次数
    '''
    def Read_Cache(self, address:np.int16):
        # 主存
        global Dmem
        self.Access_Times_Count += 1
        (Tag, Group_Index, Block_Offset) = self.Split_Address(address)
        # 遍历组内的每一行
        for i in range(0, self.ASSOCIATIVITY):
            Tag_In_Cache = self.Tag_Cache[Group_Index][i]
            Data_In_Cache = self.Data_Cache[Group_Index][i]
            # Tag匹配且valid位有效
            if Tag_In_Cache == Tag and Data_In_Cache[0] == '01':
                return Data_In_Cache[2+Block_Offset]
            
        # 组内没有匹配的行,失效次数+1,需要访问主存,将被请求的块取出放入缓存,可能还需要替换Cache中某行
        self.Miss_Times_Count += 1
        # 处理Miss的情况，从主存中取出请求的行放入Cache中
        self.Handle_Read_Miss(address)
        # 从主存中取出了相应数据，返回主存中的数据
        return Dmem[address]

    '''
    处理读不命中
    访问主存，取出请求的块
    若当前组有空闲行，则放入，否则需要替换一行
    注意采用写回,若替换的行Dirty,需要将其先写回主存中
    '''
    def Handle_Read_Miss(self, address:np.int16):
        global Dmem
        # 计算address在主存中的第几块
        seq = address//self.BLOCK_SIZE
        # 取出主存中的一块
        block = Dmem[seq*self.BLOCK_SIZE : (seq+1)*self.BLOCK_SIZE]
        (Tag, Group_Index, Block_Offset) = self.Split_Address(address)
        # 遍历当前组内是否有无效的行
        for i in range(0, self.ASSOCIATIVITY):
            # 存在空闲行
            if self.Data_Cache[Group_Index][i][0] == '00':
                self.Data_Cache[Group_Index][i][0] = '01'
                # 置空Dirty位
                self.Data_Cache[Group_Index][i][1] = '00'
                # 写入请求块的数据
                self.Data_Cache[Group_Index][i][2:] = block
                # 对应的TagCache的Tag也要修改
                self.Tag_Cache[Group_Index][i] = Tag
                return
            
        # 不存在空闲的行,这时需要在组内选出一个行来替换
        Replaced_Line_Num = self.Calc_Replaced_Line_Num()
        # 将主存中取出的请求块写入Cache,如果这个行是Dirty的,需要先将其写回主存
        if self.Data_Cache[Group_Index][Replaced_Line_Num][1] == '01':
            self.Write_Back_To_Memory(address, Replaced_Line_Num)
        self.Data_Cache[Group_Index][Replaced_Line_Num][2:] = block
        self.Tag_Cache[Group_Index][Replaced_Line_Num] = Tag

    '''
    当行替换时,如果这个行是Dirty的,需要先将其写回主存
    '''
    def Write_Back_To_Memory(self, address:np.int16, Replaced_Line_Num):
        global Dmem
        (Tag, Group_Index, Block_Offset) = self.Split_Address(address)
        seq = address//self.BLOCK_SIZE
        Dmem[seq*self.BLOCK_SIZE : (seq+1)*self.BLOCK_SIZE] = self.Data_Cache[Group_Index][Replaced_Line_Num]

    '''
    Cache替换策略,选出一个替换行,
    目前是随机替换
    '''
    def Calc_Replaced_Line_Num(self):
        return random.randint(0, self.ASSOCIATIVITY-1)

    '''
    写Cache
    给定地址和一个字节,将其写入Cache中
    采用WriteBack + Write_Allocate
    '''
    def Write_Cache(self, address:np.int16, byte):
        self.Access_Times_Count += 1
        (Tag, Group_Index, Block_Offset) = self.Split_Address(address)
        # 遍历组内的每一行
        for i in range(0, self.ASSOCIATIVITY):
            Tag_In_Cache = self.Tag_Cache[Group_Index][i]
            Data_In_Cache = self.Data_Cache[Group_Index][i]

            # Tag匹配且valid位有效,写命中
            if Tag_In_Cache == Tag and Data_In_Cache[0] == '01':
                # 置位Dirty位
                self.Data_Cache[Group_Index][i][1] = '01'
                return

        # 写不命中,采用写分配,先将主存中的整个数据块取出,合并后写入到Cache中
        self.Miss_Times_Count += 1
        self.Handle_Write_Miss(address, byte)
        return
    
    '''
    处理写不命中
    用写分配,先将主存中的整个数据块取出,合并后写入到Cache中
    '''
    def Handle_Write_Miss(self, address:np.int16, byte):
        global Dmem
        # 计算address在主存中的第几块
        seq = address//self.BLOCK_SIZE
        # 取出主存中的一块
        block = Dmem[seq*self.BLOCK_SIZE : (seq+1)*self.BLOCK_SIZE]
        (Tag, Group_Index, Block_Offset) = self.Split_Address(address)
        # 合并取出的块和写入的字节
        block[Block_Offset] = byte

        # 遍历当前组内是否有无效的行
        for i in range(0, self.ASSOCIATIVITY):
            # 存在空闲行,将block写入这个空闲行,且将其Dirty位置位
            if self.Data_Cache[Group_Index][i][0] == '00':
                self.Data_Cache[Group_Index][i][0] = '01'
                # 置位Dirty位
                self.Data_Cache[Group_Index][i][1] = '01'
                # 写入block
                self.Data_Cache[Group_Index][i][2:] = block
                # 对应的TagCache的Tag也要修改
                self.Tag_Cache[Group_Index][i] = Tag
        
        # 不存在空闲行,这时需要找一个行替换
        Replaced_Line_Num = self.Calc_Replaced_Line_Num()
        # 如果这个行是Dirty的,需要先将其写回主存
        if self.Data_Cache[Group_Index][Replaced_Line_Num][1] == '01':
            self.Write_Back_To_Memory(address, Replaced_Line_Num)
        # 将block写入这行
        self.Data_Cache[Group_Index][Replaced_Line_Num][2:] = block
        self.Tag_Cache[Group_Index][Replaced_Line_Num] = Tag

    '''
    打印出访问Cache的总次数和命中率
    '''
    def Print_Miss_Rate(self):
        print("L1_Cache:\n Total_Access Times: %d\n Miss Times: %d\nMiss Rate %f\n" \
              %(self.Access_Times_Count, self.Miss_Times_Count, self.Miss_Times_Count/self.Access_Times_Count))
# 主存的L1Cache
L1_Cache = Cache()