'''
Y86-64_Simulator_Pipe.py
========================
Y86_64流水线CPU模拟器主程序
在这个程序中,通过创建多个线程来并行模拟各个流水段
加载编写的Y86-64机器代码程序到主存中进行模拟执行
'''

from Functions import *
import threading
import Resources
import numpy as np


# 加载器，将机器码程序加载到内存中
def loadProgram(file):
    fil = open(file,'r')
    lineno = 0
    address = np.int16(0)
    while True:
        line = fil.readline()
        lineno += 1
        if (lineno == 1 or lineno == 2):
            continue
        if(line == '' or line == '\n'):
            break
        try:
            instruc = line
            instruc = instruc.strip('\n')
            instruc = instruc.split(',')[0]
            instruc = instruc.split(';')[0]
            instruc = instruc.strip(',')    #指令为字符串类型,十六进制
            instruc = instruc.strip(';')

            # print(instruc, len(instruc))
            
            for i in range(0, len(instruc)//2):
                Resources.Memory.Write_Inst_Memory(address, instruc[2*i : 2*i+2])
                address += 1
        except:
            print(f'File {file} line {lineno} has error')
            pass
    fil.close


loadProgram("test/test_speedup.coe")
print(Resources.Memory.Inst_Mem)


'''
每个周期结束时都检查CPU的状态
'''
def check():
   #print(Resources.stat)
   if(Resources.stat == 1):
      return 1
   elif(Resources.stat == 2):
      print("Error: Halt")
      return 0
   elif(Resources.stat == 3):
      print("Error: illegal address")
      return 0
   elif(Resources.stat == 4):
      print("Error: ilegal instruction")
      return 0

# 下面这些是来自于上一个周期的信号，也就是这一周期各个阶段接受的输入信号
no = 0
# 控制信号，本周期末尾计算，在下个周期生效
IF_stall = 0
ID_stall = 0
EX_bubble = 0
IF_bubble = 0
##第一个参数：IF获取的拍数；第二个参数：EX执行所剩余的周期；第三个参数：EX是否在使用
EX_cycles = [0, 0]
# IF_ID寄存器的状态，即此时刻寄存器的值
IF_ID_status = (1, 0, 0, 0, 0, 0, 0)
# (pre_valP, pre_Cnd, pre_valC, IF_icode, EX_icode, MEM_icode, pre_valM, pre_PC)
IF_input_signals = (0, 0, 0, 1, 1, 1, 0, 0)

# (IF_icode, IF_ifun, IF_rA, IF_rB, IF_valP, IF_valC, IF_PC) 
ID_input_signals =(1, 0, 0, 0, 0, 0, 0)

# (ID_icode, ID_ifun, ID_valA, ID_valB, ID_valP, ID_valC, ID_rB, ID_rA, ID_dstE, ID_dstM) 
EX_input_signals = (1, 0, 0, 0, 0, 0, 0, 0, 15, 15)

# (EX_valE, EX_valP, EX_Cnd,  EX_valC, EX_icode, EX_ifun, EX_valA, EX_rB, EX_rA, EX_dstE, EX_dstM) 
MEM_input_signals = (0, 0, 0, 0, 1, 0, 0, 0, 0, 15, 15)

# (MEM_valP, MEM_Cnd, MEM_valC, MEM_icode, MEM_valM, MEM_rB, MEM_valE, MEM_ifun, MEM_rA, MEM_dstE, MEM_dstM)  
WB_input_signals = (0, 0, 0, 1, 0, 0, 0, 0, 0, 15, 15)

# ------------------------------------------------------------------------------------------------
# 下面是本周期计算完成产生的结果信号
# 这样分离是为了避免多线程带来的共享变量临界区
# (IF_icode, IF_ifun, IF_rA, IF_rB, IF_valP, IF_valC, IF_PC)
IF_result_signals = (1, 0, 15, 15, 0, 0, 0)

# (ID_icode, ID_ifun, ID_valA, ID_valB, ID_valP, ID_valC, ID_rB, ID_rA, ID_dstE, ID_dstM)
ID_result_signals =(1, 0, 0, 0, 0, 0, 15, 15, 15, 15)

# (EX_valE, EX_valP, EX_Cnd,  EX_valC, EX_icode, EX_ifun, EX_valA, EX_rB, EX_rA, EX_dstE, EX_dstM)
EX_result_signals = (0, 0, 0, 0, 1, 0, 0, 15, 15, 15, 15)

# (MEM_valP, MEM_Cnd, MEM_valC, MEM_icode, MEM_valM, MEM_rB, MEM_valE, MEM_ifun, MEM_rA, MEM_dstE, MEM_dstM)
MEM_result_signals = (0, 0, 0, 1, 0, 0, 0, 0, 15, 15, 15)

# (WB_icode, WB_ifun, WB_dstE, WB_dstM)
WB_result_signals = (0, 0, 15, 15)


# 五个阶段的线程任务函数
# 使用上一个周期的信号进行计算，产生本周期的输出信号
# 在后面的cycle函数中，一个周期的末尾，各个阶段都已经计算完成后，将上个周期的信号值更新为本周期计算产生的新的信号值
def task_fetch():
   global IF_input_signals, IF_result_signals, IF_stall, IF_bubble
   IF_result_signals = Fetch(IF_input_signals, IF_stall, IF_bubble)
   # TODO
   # 目前未考虑任何分支或者跳转指令
   # debug
   thread_id = threading.current_thread().name
   # print(f"thread {thread_id} fetching")

def task_decode():
   global ID_input_signals, ID_result_signals
   ID_result_signals = Decode(ID_input_signals)
   # debug
   thread_id = threading.current_thread().name
   # print(f"thread {thread_id} decoding")

def task_execute():
   global EX_input_signals, EX_result_signals
   EX_result_signals = Execute(EX_input_signals)
   # debug
   thread_id = threading.current_thread().name
   # print(f"thread {thread_id} executing")

def task_memory():
   global MEM_input_signals, MEM_result_signals
   MEM_result_signals = Memory(MEM_input_signals)
   # debug
   thread_id = threading.current_thread().name
   # print(f"thread {thread_id} memorying")

def task_writeback():
   global WB_input_signals, WB_result_signals
   WB_result_signals = WriteBack(WB_input_signals)
   # debug
   thread_id = threading.current_thread().name
   # print(f"thread {thread_id} writingback")


execute = threading.Thread(target=task_execute)
'''
模拟一个周期的执行，同一时刻五个流水段（线程）各自执行自己的指令
每个周期都会检查CPU状态，若异常，则直接终止CPU
若没有异常，则cycle函数返回True
'''
def cycle():
   # 本周期即将计算的信号和来自上一周期的计算完成的信号
   global IF_result_signals, ID_result_signals, EX_result_signals, MEM_result_signals
   global IF_input_signals, ID_input_signals, EX_input_signals, MEM_input_signals, WB_input_signals
   global IF_stall, ID_stall, EX_bubble, IF_ID_status, IF_bubble, EX_cycles, execute
   global no

   # 每个周期开始（模拟时钟上升沿）刷新控制信号和寄存器的值
   # 时钟上升沿更新各个阶段的输入信号的值
   (IF_icode, IF_ifun, IF_rA, IF_rB, IF_valP, IF_valC, IF_pc) = IF_result_signals
   MEM_valM = MEM_result_signals[4]
   EX_Cnd = EX_result_signals[2]
   EX_valC = EX_result_signals[3]
   EX_icode = EX_result_signals[4]
   MEM_icode = MEM_result_signals[3]

   IF_input_signals = (IF_valP, EX_Cnd, EX_valC, IF_icode, EX_icode, MEM_icode, MEM_valM, IF_pc)

   # ID的输入来自IF_ID寄存器的输出
   (IF_ID_status, IF_ID_output) = IF_ID(IF_ID_status ,IF_result_signals, ID_stall)
   ID_input_signals = IF_ID_output

   # EX的输入来自ID_EX寄存器，EX没有被使用时
   if(EX_cycles[1] == 0):
      EX_input_signals = ID_EX(ID_result_signals, EX_bubble)

   MEM_input_signals = EX_result_signals
   WB_input_signals = MEM_result_signals

   # 创建5个线程，每个线程完成一个阶段的工作
   fetch = threading.Thread(target = task_fetch)
   decode = threading.Thread(target = task_decode) 
   # EX没有被使用，初始化EX
   if(EX_cycles[1] == 0):
      execute = threading.Thread(target=task_execute)
   memory = threading.Thread(target = task_memory)
   writeback = threading.Thread(target = task_writeback)

   fetch.start()
   decode.start()
   # EX没有被打开，打开EX同时设置EX剩余周期与打开的信号位
   if(EX_cycles[1] == 0):
      execute.start()
      EX_cycles[1] = 1
      if(EX_input_signals[0] == 6 and EX_input_signals[1] == 4):
         EX_cycles[0] = 5
      elif(EX_input_signals[0] == 6 and EX_input_signals[1] == 5):
         EX_cycles[0] = 10
      else:
         EX_cycles[0] = 1
   memory.start()
   writeback.start()

   # 每周期后1对EX还需执行周期减1
   if(EX_cycles[0] > 0):
      EX_cycles[0] -= 1

   fetch.join()
   decode.join()
   # EX执行剩余周期为0，且EX还在被使用，释放EX
   if(EX_cycles[0] == 0 and EX_cycles[1] == 1):
      execute.join()
      EX_cycles[1] = 0
   memory.join()
   writeback.join()

   ID_rA = ID_result_signals[7]; ID_rB = ID_result_signals[6];
   EX_dstM = EX_result_signals[10]; EX_dstE = EX_result_signals[9]

   IF_icode = IF_result_signals[0]; ID_icode = ID_result_signals[0]; EX_icode = EX_result_signals[4];

   MEM_dstM = MEM_result_signals[10]; MEM_dstE = MEM_result_signals[9]
   WB_dstM = WB_result_signals[3]; WB_dstE = WB_result_signals[2]

   # 在周期末尾更新控制信号,控制信号在下一个周期生效
   HD_signals = (ID_rA, ID_rB, EX_dstM, EX_dstE, MEM_dstM, MEM_dstE, WB_dstM, WB_dstE, IF_icode, ID_icode, EX_icode, EX_cycles[0])
   # print("(ID_rA, ID_rB, EX_dstM, EX_dstE, MEM_dstM, MEM_dstE, WB_dstM, WB_dstE, IF_icode, ID_icode, EX_icode, EX_cycles[0]):",HD_signals)
   (ID_stall, EX_bubble, IF_stall, IF_bubble) = Hazard_Detection(HD_signals)

   if check() == False:
      return False
   
   return True

# 令Cache的写回线程开始工作
# Resources.L1_Cache.Get_To_Work()

while True:
    if not cycle():
        break
   #  print(f"current cycle:{no}")
    no += 1
   #  print()

# print(Resources.mem)
print(Resources.reg)
Resources.L1_Cache.Release()