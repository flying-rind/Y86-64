import resources
import sys

#从address处开始，取出numbers_of_bytes个字节,返回一个字符串
def Load_Data_Memory(address, number_of_bytes):
    a = ''
    for i in range(0, number_of_bytes):
        a += resources.Dmem[address + i]
    return a

#从address处开始，取出numbers_of_bytes个字节,返回一个字符串
def Load_Inst_Memory(address, number_of_bytes):
    a = ''
    for i in range(0, number_of_bytes):
        a += resources.Imem[address + i]
    return a
 
#从address处开始，将val的number_of_bytes个字节写入内存
def Store_Data_Memory(address, number_of_bytes, val):

    if(address >= 1024):    #非法地址
        resources.stat = 3
        return
    
    val = hex(val)[2:]  #转为十六进制字符串
    length = len(val)
    if(length < 16):
        val = '0'*(16-length) + val
        #print(val)
    #注意小端格式
    for i in range(0, 8):
        resources.Dmem[address + i] = val[14 - 2*i] + val[15 - 2*i]


#十六进制转十进制,注意小端格式转换
def hex_2_dec(a):
    if(len(a) == 1):
        a = '0x' + a
        return eval(a)
    #注意字节为小端格式
    b = ''
    for i in range(0, len(a)//2):
        b = b + a[len(a) - 2 - 2*i] + a[len(a) - 1 - 2*i]
    b = '0x' + b
    return eval(b)

#设置控制码
def set_CC(valE):
    if(valE == 0):
        resources.ZF = 1
    else:
        resources.ZF = 0
    if(valE < 0):
        resources.SF = 1
    else:
        resources.SF = 0
    if(valE >= pow(2, 64)):
        resources.OF = 1
    else:
        resources.OF = 0
    return 

#判断是否跳转
def Cond(ifun):
    if(ifun == 0):
        return 1
    elif(ifun == 1):
        return (resources.SF^resources.OF) | resources.ZF
    elif(ifun == 2):
        return resources.SF^resources.OF
    elif(ifun == 3):
        return resources.ZF
    elif(ifun == 4):
        if(resources.ZF == 0):
            return 1
        else:
            return 0
    elif(ifun == 5):
        return ~(resources.SF^resources.OF)
    elif(ifun == 6):
        return ~(resources.SF^resources.OF)&~resources.ZF

# 使用上一个周期的控制信号，计算本周期PC的值
# 注意接受IF_stall信号，若为1，则阻塞PC值不变
def Compute_Next_PC(pre_signals, IF_stall):
    (pre_valP, pre_Cnd, pre_valC, pre_icode, pre_valM, pre_PC) = pre_signals
    if(pre_icode == 7):                            #jxx
        if(pre_Cnd == 1):
            next_pc =  pre_valC
        else:
            next_pc = pre_valP
    elif(pre_icode == 9):                           #ret
        next_pc = pre_valM
    else:
        next_pc = pre_valP
    # 阻塞程序计数器的值不变，仍未上个周期的PC 
    if IF_stall == 1:
        next_pc = pre_PC
    return next_pc

# 输入为上个周期的控制信号
# 当IF_stall信号为1时，阻塞IF段，保持程序计数器的值不变
def Fetch(pre_signals, IF_stall): 
    # 首先计算PC
    IF_pc = Compute_Next_PC(pre_signals, IF_stall)
    icode_ifun = Load_Inst_Memory(IF_pc, 1)
    IF_icode = hex_2_dec(icode_ifun[0])
    IF_ifun = hex_2_dec(icode_ifun[1])

    #若为halt指令，直接返回
    if(IF_icode == 0 or IF_icode == 1 ):                             #halt or nop
        IF_ifun = 0
        IF_rA = 0
        IF_rB = 0
        IF_valP = IF_pc+1
        IF_valC = 0
        if(IF_icode == 0):
            resources.stat = 2
        return (IF_icode, IF_ifun, IF_rA, IF_rB, IF_valP, IF_valC, IF_pc)

    rA_rB = Load_Inst_Memory(IF_pc+1, 1)
    IF_rA = hex_2_dec(rA_rB[0])
    IF_rB = hex_2_dec(rA_rB[1])    
    if(IF_icode == 6):                             #OPq
        IF_valP = IF_pc + 2
        IF_valC = 0
    elif(IF_icode == 2):                           #rrmovq and cmovxx
        IF_valP = IF_pc + 2
        IF_valC = 0
    elif(IF_icode == 3 and IF_ifun == 0):             #irmovq
        IF_valC = hex_2_dec(Load_Inst_Memory(IF_pc+2, 8))
        IF_valP = IF_pc + 10
    elif(IF_icode == 4 and IF_ifun == 0):             #rmmovq
        IF_valC = hex_2_dec(Load_Inst_Memory(IF_pc+2, 8))
        IF_valP = IF_pc + 10
    elif(IF_icode == 5 and IF_ifun == 0):             #mrmovq
        IF_valC = hex_2_dec(Load_Inst_Memory(IF_pc+2, 8))  
        IF_valP = IF_pc + 10
    elif(IF_icode == 10 and IF_ifun == 0):            #pushq
        IF_valP = IF_pc + 2
        IF_valC = 0
    elif(IF_icode == 11 and IF_ifun == 0):            #popq
        IF_valP = IF_pc + 2
        IF_valC = 0
    elif(IF_icode == 7):                           #jxx
        IF_valP = IF_pc + 9
        IF_valC = hex_2_dec(Load_Inst_Memory(IF_pc + 1, 8))
    elif(IF_icode == 8):                           #call
        IF_valC = hex_2_dec(Load_Inst_Memory(IF_pc + 1, 8))
        IF_valP = IF_pc + 9
    elif(IF_icode == 9):                           #ret
        IF_valP = IF_pc + 1
        IF_valC = 0

    # 未知指令，报错提醒
    else:
        print("Fetching error: invalid instruction, exit now")
        sys.exit(0)
    #返回值类型均为int
    return (IF_icode, IF_ifun, IF_rA, IF_rB, IF_valP, IF_valC, IF_pc)

# IF_ID段的流水寄存器
# 接受ID_stall信号时，保持当前状态不变
# 接受ID_bubble信号时，新传输nop信号以刷下一个阶段
# 否则将当前状态更新，输出输入
def IF_ID(status, input, ID_stall):
    if ID_stall == 1:
        output = status
        new_status = status
    else:
        output = input
        new_status = input
    return (new_status, output)

# 在Decode段产生dst_M的值，即写回寄存器的索引
def Decode(pre_signals):

    (IF_icode, IF_ifun, IF_rA, IF_rB, IF_valP, IF_valC, IF_pc) = pre_signals
    ID_icode = IF_icode; ID_ifun = IF_ifun; ID_valP = IF_valP; ID_valC = IF_valC; ID_rB = IF_rB; ID_rA = IF_rA
    if(ID_icode == 6):                             #OPq
        ID_valA = resources.reg[ID_rA]
        ID_valB = resources.reg[ID_rB]
        ID_dstM = None
        ID_dstE = ID_rB
    elif(ID_icode == 1):                            # nop
        ID_valA = 0
        ID_valB = 0
        ID_dstM = None
        ID_dstE = None
    elif(ID_icode == 2):                           #rrmovq and cmovxx
        ID_valA = resources.reg[ID_rA]
        ID_valB = 0
        ID_dstM = None
        ID_dstE = ID_rB
    elif(ID_icode == 3 and ID_ifun == 0):             #irmovq
        ID_valA = resources.reg[ID_rA]
        ID_valB = resources.reg[ID_rB]
        ID_dstM = None
        ID_dstE = ID_rB
    elif(ID_icode == 4 and ID_ifun == 0):             #rmmovq
        ID_valA = resources.reg[ID_rA]
        ID_valB = resources.reg[ID_rB]
        ID_dstM = None
        ID_dstE = None
    elif(ID_icode == 5 and ID_ifun == 0):             #mrmovq
        ID_valA = resources.reg[ID_rA]
        ID_valB = resources.reg[ID_rB]
        ID_dstM = ID_rA
        ID_dstE = None
    elif(ID_icode == 10 and ID_ifun == 0):            #pushq
        ID_valA = resources.reg[ID_rA]
        ID_valB = resources.reg[4]
        ID_dstM = None
        ID_dstE = 4
    elif(ID_icode == 11 and ID_ifun == 0):            #popq
        ID_valA = resources.reg[4]
        ID_valB = resources.reg[4]
        ID_dstM = ID_rA
        ID_dstE = 4
    elif(ID_icode == 7):                           #jxx
        ID_valA = 0
        ID_valB = 0
        ID_dstM = None
        ID_dstE = None
    elif(ID_icode == 8):                           #call
        ID_valA = 0
        ID_valB = resources.reg[4]
        ID_dstM = None
        ID_dstE = 4
    elif(ID_icode == 9):                           #ret
        ID_valA = resources.reg[4]
        ID_valB = resources.reg[4]
        ID_dstM = None
        ID_dstE = 4
    # 未知指令，报错提醒
    else:
        print("Decoding error: invalid instruction, exit now")
        sys.exit(0)
    return (ID_icode, ID_ifun, ID_valA, ID_valB, ID_valP, ID_valC, ID_rB, ID_rA, ID_dstE, ID_dstM)
#返回值均为int类型

# ID到EX段之间的流水线寄存器，接受EX_bubble信号，其有效时，寄存器给出一个气泡以刷新后面阶段的指令
def ID_EX(input, EX_bubble):
    # 产生nop指令对应的信号，以刷新后面的指令
    if EX_bubble == 1:
        return(1, 0, None, None, None, None, None, None, None, None)
    return input


def Execute(pre_signals):
    (ID_icode, ID_ifun, ID_valA, ID_valB, ID_valP, ID_valC, ID_rB, ID_rA, ID_dstE, ID_dstM) = pre_signals
    EX_valP = ID_valP; EX_valC = ID_valC; EX_icode = ID_icode; EX_ifun = ID_ifun; EX_valA = ID_valA; EX_rB = ID_rB; EX_rA = ID_rA; EX_dstE = ID_dstE; EX_dstM = ID_dstM
    if(EX_icode == 6):                             #OPq
        op = resources.OP[EX_ifun]
        EX_valE = eval( str(ID_valB) + op + str(ID_valA) )
        set_CC(EX_valE)
        EX_Cnd = 0
    elif(EX_icode == 1):                           # nop
        EX_valE = 0
        EX_Cnd = 0
    elif(EX_icode == 2):                           #rrmovq and cmovxx
        EX_valE = 0 + ID_valA
        EX_Cnd = Cond(EX_ifun)
    elif(EX_icode == 3 and EX_ifun == 0):             #irmovq
        EX_valE = 0 + ID_valC
        EX_Cnd = 0
    elif(EX_icode == 4 and EX_ifun == 0):             #rmmovq
        EX_valE = ID_valB + ID_valC
        EX_Cnd = 0
    elif(EX_icode == 5 and EX_ifun == 0):             #mrmovq
        EX_valE = ID_valB + ID_valC
        EX_Cnd = 0          
    elif(EX_icode == 10 and EX_ifun == 0):            #pushq
        EX_valE = ID_valB - 8
        EX_Cnd = 0
    elif(EX_icode == 11 and EX_ifun == 0):            #popq
        EX_valE = ID_valB + 8
        EX_Cnd = 0
    elif(EX_icode == 7):                           #jxx
        EX_valE = 0
        EX_Cnd = Cond(EX_ifun)
    elif(EX_icode == 8):                           #call
        EX_valE = ID_valB - 8
        EX_Cnd = 0
    elif(EX_icode == 9):                           #ret
        EX_valE = ID_valB + 8
        EX_Cnd = 0
    # 未知指令，报错提醒
    else:
        print("Executing error: invalid instruction, exit now")
        sys.exit(0)
    return (EX_valE, EX_valP, EX_Cnd,  EX_valC, EX_icode, EX_ifun, EX_valA, EX_rB, EX_rA, EX_dstE, EX_dstM)


def Memory(pre_signals):
    (EX_valE, EX_valP, EX_Cnd,  EX_valC, EX_icode, EX_ifun, EX_valA, EX_rB, EX_rA, EX_dstE, EX_dstM) = pre_signals
    MEM_valP = EX_valP; MEM_Cnd = EX_Cnd; MEM_valC = EX_valC; MEM_icode = EX_icode; MEM_rB = EX_rB; MEM_valE = EX_valE; MEM_ifun = EX_ifun; MEM_rA = EX_rA; MEM_dstE = EX_dstE; MEM_dstM = EX_dstM
    if(MEM_icode == 6):                             #OPq
        MEM_valM = 0
    elif(MEM_icode == 1):                           # nop
        MEM_valM = 0
    elif(MEM_icode == 2):                           #rrmovq and cmovxx
        MEM_valM = 0
    elif(MEM_icode == 3 and MEM_ifun == 0):             #irmovq
        MEM_valM = 0
    elif(MEM_icode == 4 and MEM_ifun == 0):             #rmmovq
        Store_Data_Memory(EX_valE, 8, EX_valA)
        MEM_valM = 0
    elif(MEM_icode == 5 and MEM_ifun == 0):             #mrmovq
        MEM_valM = hex_2_dec(Load_Data_Memory(EX_valE, 8))
    elif(MEM_icode == 10 and MEM_ifun == 0):            #pushq
        Store_Data_Memory(EX_valE, 8, EX_valA)
        MEM_valM = 0
    elif(MEM_icode == 11 and MEM_ifun == 0):            #popq
        MEM_valM = hex_2_dec(Load_Data_Memory(EX_valA, 8))
    elif(MEM_icode == 7):                           #jxx
        MEM_valM = 0
    elif(MEM_icode == 8):                           #call
        Store_Data_Memory(EX_valE, 8, EX_valP)
        MEM_valM = 0
    elif(MEM_icode == 9):                           #ret
        MEM_valM = hex_2_dec(Load_Data_Memory(EX_valA, 8))
    # 未知指令，报错提醒
    else:
        print("Memorying error: invalid instruction, exit now")
        sys.exit(0)
    return (MEM_valP, MEM_Cnd, MEM_valC, MEM_icode, MEM_valM, MEM_rB, MEM_valE, MEM_ifun, MEM_rA, MEM_dstE, MEM_dstM)

def WriteBack(pre_signals):     
    (MEM_valP, MEM_Cnd, MEM_valC, MEM_icode, MEM_valM, MEM_rB, MEM_valE, MEM_ifun, MEM_rA, MEM_dstE, MEM_dstM) = pre_signals
    WB_icode = MEM_icode; WB_ifun = MEM_ifun; WB_dstE = MEM_dstE; WB_dstM = MEM_dstM
    if(WB_icode == 6):                             #OPq
        resources.reg[MEM_rB] = MEM_valE
    elif(WB_icode == 1):                           # nop
        pass
    elif(WB_icode == 2):                           #rrmovq and cmovxx
        if(MEM_Cnd == 1):
            resources.reg[MEM_rB] = MEM_valE
    elif(WB_icode == 3 and WB_ifun == 0):             #irmovq
        resources.reg[MEM_rB] = MEM_valE
    elif(WB_icode == 4 and WB_ifun == 0):             #rmmovq
        pass
    elif(WB_icode == 5 and WB_ifun == 0):             #mrmovq
        resources.reg[MEM_rA] = MEM_valM
    elif(WB_icode == 10 and WB_ifun == 0):            #pushq
        resources.reg[4] = MEM_valE
    elif(WB_icode == 11 and WB_ifun == 0):            #popq
        resources.reg[4] = MEM_valE
        resources.reg[MEM_rA] = MEM_valM  
    elif(WB_icode == 7):                           #jxx
        pass
    elif(WB_icode == 8):                           #call
        resources.reg[4] = MEM_valE
    elif(WB_icode == 9):                           #ret
        resources.reg[4] = MEM_valE
    # 未知指令，报错提醒
    else:
        print("Writing back error: invalid instruction, exit now")
        sys.exit(0)
        
    return(WB_icode, WB_ifun, WB_dstE, WB_dstM)


# 冲突检测模块，用于产生阻塞和气泡的信号
def Hazard_Detection(HD_signals):
    (ID_rA, ID_rB, EX_dstM, EX_dstE, MEM_dstM, MEM_dstE, WB_dstM, WB_dstE) = HD_signals
    ID_stall = EX_bubble = IF_stall = 0
    if ID_rA == EX_dstM or ID_rA == EX_dstE or ID_rA == MEM_dstM or ID_rA == MEM_dstE or ID_rA == WB_dstM or ID_rA == WB_dstE and ID_rA != None:
        ID_stall = EX_bubble = IF_stall = 1
    if ID_rB == EX_dstM or ID_rB == EX_dstE or ID_rB == MEM_dstM or ID_rB == MEM_dstE or ID_rB == WB_dstM or ID_rB == WB_dstE and ID_rB != None:
        ID_stall = EX_bubble = IF_stall = 1
    return (IF_stall, ID_stall, EX_bubble)
print("running")        