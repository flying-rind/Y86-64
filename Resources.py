'''
Resources.py
============
这个py文件中包含了CPU中的各个资源部件的定义和实现,包括了：
1. 寄存器和状态码
2. 主存
3. Cache
'''

import math
import random
import time
import threading
import numpy as np
     
# 主存最大容量
Max_Memory_Size = 98304

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


class Main_Memory:
    '''
    Main_Memory:主存类
    =================
    主存中以字节为单位存储,以两个十六进制字符表示一个字节,例如'0F'
    提供读写内存的接口,主存只有一个读写接口任意时刻读或写主存都会
    导致主存进入忙状态采用了写缓冲,当主存空闲时,写缓冲将自己的缓存
    内容写入主存
    '''
    # 忙标记
    global Max_Memory_Size
    # 为主存分配空间,内存地址空间为16位
    Data_Mem = np.full(Max_Memory_Size, "00")
    Inst_Mem = np.full(Max_Memory_Size, "00")
    # 主存的锁,任何时刻,只有一个线程能够写或者读主存Data_Mem
    lock = threading.Lock()

    def __init__(self):
        self.Busy = False

    
    def Read_Data_Memory(self, address:np.uint32, len):
        '''
        数据主存读访问接口,给定起始地址和访存长度
        给定地址返回取出的字节块(字符串)访问开始时
        将主存设为忙状态,结束时释放忙状态
        '''
        # 读内存不需要加锁
        byte = self.Data_Mem[address:address+len]
        return byte
    
   
    def Write_Data_Memory(self, start_address:np.uint32, data_block):
        '''
        主存写接口
        给定写起始地址和终止地址和写入的数据块,将数据块写入主存
        data_block是np数组类型
        写开始时设为忙状态,结束时释放忙状态
        '''
        # with lock会自动申请锁和释放锁
        with self.lock:
            self.Data_Mem[start_address:start_address + len(data_block)] = data_block

    
    def Read_Inst_Memory(self, address):
        '''
        读指令Mem,给定地址,读出一个字节
        由于目前IMem未采用Cache,直接取出
        '''
        return self.Inst_Mem[address]
    
    
    def Write_Inst_Memory(self, address, byte):
        '''
        写指令Mem,给定地址,写入一个字节
        由于目前IMem未采用Cache,直接写入
        '''
        self.Inst_Mem[address] = byte
        return

# 创建主存
Memory = Main_Memory()


class Data_Cache:
    '''
    Data_Cache:与主存直接相连的Cache
    ===============================
    采用组相联,替换策略为随机替换
    写Cache时采用写回,写不命中时采用写分配
    且Cache具有写缓冲,写缓冲采用了写合并的策略
    '''
    # Cache的总大小
    CACHE_SIZE = 4096
    # 写缓冲的最大条目数量
    WRITE_BUFFER_SIZE = 8
    # 统计总访问次数
    Access_Times_Count = 0
    # 统计失效次数
    Miss_Times_Count = 0
    # 写缓冲,是一个字典的列表,每个元素都是一个字典,包含address和数据块两个字段
    Write_Buffer = []
    # 写缓冲长度
    Write_Buffer_Length = 0
    # 写缓冲区互斥访问,需要加锁
    Write_Buffer_Lock = threading.Lock()
    # 写回线程,当主存空闲时择机将写缓冲区内的条目写回主存
    Write_Back_Thread = None
    # 线程开始的信号
    Terminate = False
    
    
    def __init__(self, BLOCK_SIZE:int = 8, ASSOCIATIVITY:int = 4):
        '''
        Cache默认为2路组相联,块大小为16
        Cache将Data_Cache(字节为单位,每个单元存放长度为2的字符串)和Tag_Cache(每个单元存放一个int型)分离
        '''
        self.BLOCK_SIZE = BLOCK_SIZE
        self.ASSOCIATIVITY = ASSOCIATIVITY
        # 组数和组索引需要的位数
        Groups = self.CACHE_SIZE//BLOCK_SIZE//ASSOCIATIVITY
        self.Group_Index_Bits = int(math.log(Groups, 2))
        # 块偏移需要的位数
        self.Block_Offset_Bits = int(math.log(self.BLOCK_SIZE, 2))
        # 标记需要的位数
        self.Tag_Bits = 16 - self.Block_Offset_Bits - self.Group_Index_Bits

        print("L1 Data Cache, Groups: %d, Lines each Group: %d, bytes per Line: %d" %(Groups, ASSOCIATIVITY, BLOCK_SIZE))
        print('Physical address => Tag(%d)bits, Group_Index(%d)bits, Block_Offset(%d)bits' %(self.Tag_Bits, self.Group_Index_Bits, self.Block_Offset_Bits))

        # 分配DataCache(每行包含一个valid位和dirty位)和TagCache
        self.Data_Cache = np.full((Groups, ASSOCIATIVITY, BLOCK_SIZE+2), "00")
        self.Tag_Cache = np.full((Groups, ASSOCIATIVITY), 0, dtype = int)

        self.Write_Back_Thread = threading.Thread(name = 'WriteBack', target = self.Write_Buffer_2_Memory)
        self.Write_Back_Thread.start()

    
    def Release(self):
        '''
        回收线程,打印访存命中率等信息
        打印出访问Cache的总次数和命中率
        '''
        self.Terminate = True
        self.Write_Back_Thread.join()
        print("L1_Cache:\nTotal_Access Times: %d\nMiss Times: %d" \
              %(self.Access_Times_Count, self.Miss_Times_Count))
        
        if self.Miss_Times_Count != 0:
            print('Miss rate = %f %%' %(self.Miss_Times_Count/self.Access_Times_Count*100))
    

    
    def Split_Address(self, address:np.uint32):
        '''
        给定一个地址,返回地址拆分后得到的
        (Tag, Group_Index, Block_Offset)
        (int, int, int)
        '''
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
    
    
    def Read_Cache(self, address:np.uint32) -> str:
        '''
        读取Cache
        address:np.uint32
        str:长度为16的字符串

        给定访存起始地址,返回读取到的8个字节（长度为16的字符串）
        访问时更新访问总次数和失效次数
        '''
        # 主存
        global Memory
        byte = ''
        self.Access_Times_Count += 1
        (Tag, Group_Index, Block_Offset) = self.Split_Address(address)
        # 这时不用跨越一个行,直接取出一整行即可
        if Block_Offset == 0:
            # 遍历组内的每一行
            for i in range(0, self.ASSOCIATIVITY):
                Tag_In_Cache = self.Tag_Cache[Group_Index][i]
                Data_In_Cache = self.Data_Cache[Group_Index][i]
                # Tag匹配且valid位有效,
                if Tag_In_Cache == Tag and Data_In_Cache[0] == '01':
                    byte = ''.join(Data_In_Cache[2:].tolist())
                    return byte
            # 读不命中,这时需要先查写缓冲,若没查到,再查主存
            byte = self.Handle_Read_Miss(address)
            self.Miss_Times_Count += 1
            return byte
        # 需要读取两个行的内容
        else:
            # 先处理第一行
            Found = False
            for i in range(0, self.ASSOCIATIVITY):
                Tag_In_Cache = self.Tag_Cache[Group_Index][i]
                Data_In_Cache = self.Data_Cache[Group_Index][i]

                # Tag匹配且valid位有效,读命中
                if Tag_In_Cache == Tag and Data_In_Cache[0] == '01':
                    byte = ''.join(Data_In_Cache[2+Block_Offset:].tolist())
                    Found = True
                    break
            # 第一行读不命中
            if Found == False:
                self.Miss_Times_Count += 1
                byte = self.Handle_Read_Miss(address)[2*Block_Offset:]
    
            # 再处理多余部分
            address += (self.BLOCK_SIZE - Block_Offset)
            # 剩余部分还有多少字节需要读
            num_bytes = Block_Offset
            (Tag, Group_Index, Block_Offset) = self.Split_Address(address)
            # 遍历组内的每一行
            for i in range(0, self.ASSOCIATIVITY):
                Tag_In_Cache = self.Tag_Cache[Group_Index][i]
                Data_In_Cache = self.Data_Cache[Group_Index][i]

                # Tag匹配且valid位有效,且这个块不是Dirty的,写命中
                if Tag_In_Cache == Tag and Data_In_Cache[0] == '01':
                    byte += ''.join(Data_In_Cache[2:2+num_bytes].tolist())
                    return byte
            # 第二行读不命中
            if Found != False:
                self.Miss_Times_Count += 1
            byte += self.Handle_Read_Miss(address)[:2*num_bytes]

        # debug
        # print("byte = ", byte)
        # print("type(byte) = ", type(byte))
        return byte

    
    def Handle_Read_Miss(self, address:np.uint32) -> str:
        '''
        处理读不命中
        address:np.uint32
        返回str,八字节的字符串

        采用写缓冲,先访问写缓冲区中的Dirty行
        若写缓冲中没有找到,访问主存，取出请求的块
        若当前组有空闲行,则放入，否则需要替换一行
        注意采用写回,若替换的行Dirty,需要将其先写回主存中
        '''
        
        # debug
        # print('Read miss happened')
        global Memory
        # 先查找写缓冲中的Dirty行,若找到,将Found置为True
        Found = False
        block = None
        for entry in self.Write_Buffer:
            dirty_line_address = entry['address']
            # Tag和Index都匹配
            if (dirty_line_address >> self.Block_Offset_Bits) == (address >> self.Block_Offset_Bits):
                block = entry['data_block']
                Found = True
                break
        
        # 写缓冲区内没有匹配的行,这时从主存中取出数据块
        if Found == False:
            # 计算address在主存中的第几块
            seq = address//self.BLOCK_SIZE
            # 取出主存中的一块
            block = Memory.Read_Data_Memory(seq*self.BLOCK_SIZE, self.BLOCK_SIZE)
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
                return ''.join(block.tolist())
            
        # 不存在空闲的行,这时需要在组内选出一个行来替换
        Replaced_Line_Num = self.Calc_Replaced_Line_Num()
        # 将主存中取出的请求块写入Cache,如果这个行是Dirty的,需要先将其写回主存
        if self.Data_Cache[Group_Index][Replaced_Line_Num][1] == '01':
            self.Write_To_Buffer(address, Replaced_Line_Num)
        self.Data_Cache[Group_Index][Replaced_Line_Num][2:] = block
        self.Tag_Cache[Group_Index][Replaced_Line_Num] = Tag

        return ''.join(block.tolist())

    
    def Write_To_Buffer(self, address:np.uint32, Replaced_Line_Num:int):
        '''
        当行替换时,如果这个行是Dirty的,将这个Dirty行加入到写缓冲中
        采用写合并策略,如果写入的行能和以前的行合并,则进行合并
        '''

        # 创建一个字典条目,将其加入写缓冲列表
        (Tag, Group_Index, Block_Offset) = self.Split_Address(address)

        merge_flag = False

        # 首先查看目前写缓冲,判断是否能够合并
        for i in range(self.Write_Buffer_Length):
            entry_address = self.Write_Buffer[i]['address']
            # 要写入写缓冲的地址和写缓冲中条目的地址属于同一块,则进行合并
            if (entry_address >> self.Block_Offset_Bits) == (address >> self.Block_Offset_Bits):
                # debug
                # print("Write_Merge happened")

                self.Write_Buffer[i]['data_block'][Block_Offset] = self.Data_Cache[Group_Index][Replaced_Line_Num][Block_Offset]
                merge_flag = True
                break

        # 不能进行写合并,则新建一个写缓冲条目
        if merge_flag == False:
            entry = {}
            entry['address'] = address
            entry['data_block'] = self.Data_Cache[Group_Index][Replaced_Line_Num][2:]
            # 写入写缓冲,注意如果写缓冲区已满,则需要阻塞,等待缓冲区空时才能写入
            while self.Write_Buffer_Length == self.WRITE_BUFFER_SIZE:
                pass
            # 写入时需要加锁
            with self.Write_Buffer_Lock:
                self.Write_Buffer.append(entry)
                self.Write_Buffer_Length += 1
            # print("Wrote to write buffer")

    
    def Calc_Replaced_Line_Num(self):
        '''
        Cache替换策略,选出一个替换行,
        目前是随机替换
        '''
        return random.randint(0, self.ASSOCIATIVITY-1)

    
    def Write_Cache(self, address:np.uint32, byte):
        '''
        写Cache
        address:np.uint32
        byte:np长度为2的字符串数组,长度即为
        块大小(8)

        给定地址和八个字节,将其写入Cache中
        采用WriteBack + Write_Allocate
        '''
        # debug
        # print("Writing to cache")

        # 检查byte长度是否为8（块大小）
        if len(byte)!= 8:
            print(len(byte))
            exit("byte length mismatch")

        self.Access_Times_Count += 1
        (Tag, Group_Index, Block_Offset) = self.Split_Address(address)
        # 这时不用跨越一个行
        if Block_Offset == 0:
            # 遍历组内的每一行
            for i in range(0, self.ASSOCIATIVITY):
                Tag_In_Cache = self.Tag_Cache[Group_Index][i]
                Data_In_Cache = self.Data_Cache[Group_Index][i]

                # Tag匹配且valid位有效,且这个块不是Dirty的,写命中
                if Tag_In_Cache == Tag and Data_In_Cache[0] == '01' and Data_In_Cache[1] == '00':
                    # 字节写入Cache
                    self.Data_Cache[Group_Index][i][2:] = byte
                    # 置位Dirty位
                    self.Data_Cache[Group_Index][i][1] = '01'
                    return
                # 找到匹配的行,但是它是Dirty的,先将其写入写缓冲
                elif Tag_In_Cache == Tag and Data_In_Cache[0] == '01' and Data_In_Cache[1] == '01':
                    self.Write_To_Buffer(address, i)
                    self.Data_Cache[Group_Index][i][2:] = byte
                    self.Data_Cache[Group_Index][i][0] = '01'
                    self.Data_Cache[Group_Index][i][1] = '01'
                    return
            # 写不命中,采用写分配,先将主存中的整个数据块取出,合并后写入到Cache中
            self.Miss_Times_Count += 1
            self.Handle_Write_Miss(address, byte)
        
        # 这时需要写入两个组,（两个组不一定在同一行）
        else:
            # 先处理第一行
            Found = False
            for i in range(0, self.ASSOCIATIVITY):
                Tag_In_Cache = self.Tag_Cache[Group_Index][i]
                Data_In_Cache = self.Data_Cache[Group_Index][i]

                # Tag匹配且valid位有效,且这个块不是Dirty的,写命中
                if Tag_In_Cache == Tag and Data_In_Cache[0] == '01' and Data_In_Cache[1] == '00':
                    # 连续字节写入Cache
                    self.Data_Cache[Group_Index][i][2+Block_Offset:] = byte[:self.BLOCK_SIZE - Block_Offset]
                    # 置位Dirty位
                    self.Data_Cache[Group_Index][i][1] = '01'
                    Found = True
                    break
                # 找到匹配的行,但是它是Dirty的,先将其写入写缓冲
                elif Tag_In_Cache == Tag and Data_In_Cache[0] == '01' and Data_In_Cache[1] == '01':
                    self.Write_To_Buffer(address, i)
                    self.Data_Cache[Group_Index][i][2+Block_Offset:] = byte[:self.BLOCK_SIZE - Block_Offset]
                    self.Data_Cache[Group_Index][i][0] = '01'
                    self.Data_Cache[Group_Index][i][1] = '01'
                    Found = True
                    break
            # 第一行写不命中
            if Found == False:
                self.Miss_Times_Count += 1
                # 写不命中,采用写分配,先将主存中的整个数据块取出,合并后写入到Cache中
                self.Handle_Write_Miss(address, byte[:self.BLOCK_SIZE - Block_Offset])

            
            # 再处理多余的部分
            address += (self.BLOCK_SIZE - Block_Offset)
            # 剩余部分还有多少字节写入下一行
            num_bytes = Block_Offset
            (Tag, Group_Index, Block_Offset) = self.Split_Address(address)
            # 遍历组内的每一行
            for i in range(0, self.ASSOCIATIVITY):
                Tag_In_Cache = self.Tag_Cache[Group_Index][i]
                Data_In_Cache = self.Data_Cache[Group_Index][i]

                # Tag匹配且valid位有效,且这个块不是Dirty的,写命中
                if Tag_In_Cache == Tag and Data_In_Cache[0] == '01' and Data_In_Cache[1] == '00':
                    # 字节写入Cache
                    self.Data_Cache[Group_Index][i][2:2+num_bytes] = byte[self.BLOCK_SIZE-num_bytes:]
                    # 置位Dirty位
                    self.Data_Cache[Group_Index][i][1] = '01'
                    return
                # 找到匹配的行,但是它是Dirty的,先将其写入写缓冲
                elif Tag_In_Cache == Tag and Data_In_Cache[0] == '01' and Data_In_Cache[1] == '01':
                    self.Write_To_Buffer(address, i)
                    self.Data_Cache[Group_Index][i][2:2+num_bytes] = byte[self.BLOCK_SIZE-num_bytes:]
                    self.Data_Cache[Group_Index][i][0] = '01'
                    self.Data_Cache[Group_Index][i][1] = '01'
                    return
            # 第二行写不命中
            if Found != False:
                self.Miss_Times_Count += 1
            self.Handle_Write_Miss(address, byte[self.BLOCK_SIZE-num_bytes:])
    
    def Handle_Write_Miss(self, address:np.uint32, byte):
        '''
        处理写不命中
        address:np.uint32
        byte:np长度为2的字符串的数组,长度不确定,
        用写分配,先将主存中的整个数据块取出,合并后写入到Cache中
        '''

        # debug
        # print('Write miss happened')
        global Memory
        # 计算address在主存中的第几块
        seq = address//self.BLOCK_SIZE
        # 取出主存中的一块
        block = Memory.Read_Data_Memory(seq*self.BLOCK_SIZE, self.BLOCK_SIZE)
        (Tag, Group_Index, Block_Offset) = self.Split_Address(address)
        # 合并取出的块和写入的字节
        block[0:len(byte)] = byte

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
            self.Write_To_Buffer(address, Replaced_Line_Num)
        # 将block写入这行
        self.Data_Cache[Group_Index][Replaced_Line_Num][2:] = block
        self.Tag_Cache[Group_Index][Replaced_Line_Num] = Tag
        # 修改Valid位和Dirty位
        self.Data_Cache[Group_Index][Replaced_Line_Num][0] = '01'
        self.Data_Cache[Group_Index][Replaced_Line_Num][1] = '01'

    
    def Write_Buffer_2_Memory(self):
        '''
        将Write_Buffer中的内容择机写回Data_Memory,注意主存的互斥访问
        将这个函数作为线程函数,不断等待主存空闲时刻,将buffer内容写入 
        '''
        global Memory
        while True:
            # 注意回收线程
            if self.Terminate == True:
                return
            # time.sleep(0.5)
            if len(self.Write_Buffer) <= self.WRITE_BUFFER_SIZE//2:
                continue
            # 由于Write_Data_Memory函数中会加锁,这里不需要显式地加锁
            for entry in self.Write_Buffer:
                address = entry['address']
                data_block = entry['data_block']
                Memory.Write_Data_Memory(address, data_block)
            # print('Wrote write buffer to main memory')
            # 清空自己的写缓冲区,注意需要加锁
            with self.Write_Buffer_Lock:
                self.Write_Buffer = []
                self.Write_Buffer_Length = 0

# 主存的L1Cache
L1_Cache = Data_Cache()