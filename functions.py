import Resources
import sys

#从address处开始，取出numbers_of_bytes个字节,返回一个字符串
def Load_Data_Memory(address, number_of_bytes):
    a = ''
    for i in range(0, number_of_bytes):
        a += Resources.Dmem[address + i]
    return a

#从address处开始，取出numbers_of_bytes个字节,返回一个字符串
def Load_Inst_Memory(address, number_of_bytes):
    a = ''
    for i in range(0, number_of_bytes):
        a += Resources.Imem[address + i]
    return a
 
#从address处开始，将val的number_of_bytes个字节写入内存
def Store_Data_Memory(address, number_of_bytes, val):
    if(address >= 4096):    #非法地址
        # debug
        # print("accessing illegal memory address %d" % address)
        Resources.stat = 3
        return
    
    val = hex(val)[2:]  #转为十六进制字符串
    length = len(val)
    if(length < 16):
        val = '0'*(16-length) + val
        #print(val)
    #注意小端格式
    for i in range(0, 8):
        Resources.Dmem[address + i] = val[14 - 2*i] + val[15 - 2*i]


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
        Resources.ZF = 1
    else:
        Resources.ZF = 0
    if(valE < 0):
        Resources.SF = 1
    else:
        Resources.SF = 0
    if(valE >= pow(2, 64)):
        Resources.OF = 1
    else:
        Resources.OF = 0
    return 

#判断是否跳转
def Cond(ifun):
    if(ifun == 0):
        return 1
    elif(ifun == 1):
        return (Resources.SF^Resources.OF) | Resources.ZF
    elif(ifun == 2):
        return Resources.SF^Resources.OF
    elif(ifun == 3):
        return Resources.ZF
    elif(ifun == 4):
        if(Resources.ZF == 0):
            return 1
        else:
            return 0
    elif(ifun == 5):
        return ~(Resources.SF^Resources.OF)
    elif(ifun == 6):
        return ~(Resources.SF^Resources.OF)&~Resources.ZF

# 使用上一个周期的控制信号，计算本周期PC的值
# 注意接受IF_stall信号，若为1，则阻塞PC值不变
def Compute_Next_PC(pre_signals, IF_stall, IF_bubble):
    (pre_valP, pre_Cnd, pre_valC, IF_icode, EX_icode, MEM_icode, pre_valM, pre_PC) = pre_signals
    if(EX_icode == 7):                             # jxx
        if(pre_Cnd == 1):
            next_pc =  pre_valC
        else:
            next_pc = pre_valP
    elif IF_icode == 8:                             # call
        next_pc = pre_valC
    elif(MEM_icode == 9):                           # ret
        next_pc = pre_valM
    else:                                           # 顺序执行
        next_pc = pre_valP
    # 阻塞程序计数器的值不变，仍未上个周期的PC 
    if IF_stall == 1:
        next_pc = pre_PC

    # 若为-1，表示是我们插入的nop指令
    if IF_bubble == 1:
        next_pc = pre_PC
    return next_pc

# 输入为上个周期的控制信号
# 当IF_stall信号为1时，阻塞IF段，保持程序计数器的值不变
# 当IF_bubble信号为1时，下一条指令取出为nop
def Fetch(pre_signals, IF_stall, IF_bubble): 
    # 首先计算PC
    IF_pc = Compute_Next_PC(pre_signals, IF_stall, IF_bubble)
    # debug
    # print("IF_pc = %d" %IF_pc)

    icode_ifun = Load_Inst_Memory(IF_pc, 1)
    IF_icode = hex_2_dec(icode_ifun[0])
    IF_ifun = hex_2_dec(icode_ifun[1])

    # 如果bubble信号有效，就刷新为nop指令,当stall信号和bubble信号同时生效时，采用阻塞
    if IF_bubble == 1 and IF_stall != 1:
        IF_icode = 1
        IF_ifun = 0

    # debug
    # print("IF_icode: %d" %IF_icode)

    #若为halt指令，直接返回
    if(IF_icode == 0 or IF_icode == 1 ):                             #halt or nop
        IF_ifun = 0
        IF_rA = 15
        IF_rB = 15
        IF_valP = IF_pc+1
        IF_valC = 0
        if(IF_icode == 0):
            Resources.stat = 2
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
        IF_rA = 15
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
        IF_rB = 15
    elif(IF_icode == 7):                              #jxx
        IF_valP = IF_pc + 9
        IF_valC = hex_2_dec(Load_Inst_Memory(IF_pc + 1, 8))
        IF_rA = 15; IF_rB = 15
    elif(IF_icode == 8):                           #call
        IF_valC = hex_2_dec(Load_Inst_Memory(IF_pc + 1, 8))
        IF_rA = 15; IF_rB = 15

        # debug
        # print("IF_valC = %d" % IF_valC)

        IF_valP = IF_pc + 9
    elif(IF_icode == 9):                           #ret
        IF_valP = IF_pc + 1
        IF_valC = 0

    # 未知指令，报错提醒
    else:
        # print("Fetching error: invalid instruction, exit now")
        sys.exit(0)
    #返回值类型均为int
    return (IF_icode, IF_ifun, IF_rA, IF_rB, IF_valP, IF_valC, IF_pc)

# IF_ID段的流水寄存器
# 接受ID_stall信号时，保持当前状态不变
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

    # debug
    # print("ID_icode: %d" %ID_icode)

    if(ID_icode == 6):                             #OPq
        ID_valA = Resources.reg[ID_rA]
        ID_valB = Resources.reg[ID_rB]
        ID_dstM = 15
        ID_dstE = ID_rB
    elif(ID_icode == 1):                            # nop
        ID_valA = 0
        ID_valB = 0
        ID_dstM = 15
        ID_dstE = 15
    elif(ID_icode == 2):                           #rrmovq and cmovxx
        ID_valA = Resources.reg[ID_rA]
        ID_valB = 0
        ID_dstM = 15
        ID_dstE = ID_rB
    elif(ID_icode == 3 and ID_ifun == 0):             #irmovq
        ID_valA = Resources.reg[ID_rA]
        ID_valB = Resources.reg[ID_rB]
        ID_dstM = 15
        ID_dstE = ID_rB
    elif(ID_icode == 4 and ID_ifun == 0):             #rmmovq
        ID_valA = Resources.reg[ID_rA]
        ID_valB = Resources.reg[ID_rB]
        ID_dstM = 15
        ID_dstE = 15
    elif(ID_icode == 5 and ID_ifun == 0):             #mrmovq
        ID_valA = Resources.reg[ID_rA]
        ID_valB = Resources.reg[ID_rB]
        ID_dstM = ID_rA
        ID_dstE = 15
    elif(ID_icode == 10 and ID_ifun == 0):            #pushq
        ID_valA = Resources.reg[ID_rA]
        ID_valB = Resources.reg[4]
        ID_dstM = 15
        ID_dstE = 4
    elif(ID_icode == 11 and ID_ifun == 0):            #popq
        ID_valA = Resources.reg[4]
        ID_valB = Resources.reg[4]
        ID_dstM = ID_rA
        ID_dstE = 4
    elif(ID_icode == 7):                           #jxx
        ID_valA = 0
        ID_valB = 0
        ID_dstM = 15
        ID_dstE = 15
    elif(ID_icode == 8):                           #call
        ID_valA = 0
        ID_valB = Resources.reg[4]
        ID_dstM = 15
        ID_dstE = 4
    elif(ID_icode == 9):                           #ret
        ID_valA = Resources.reg[4]
        ID_valB = Resources.reg[4]
        ID_dstM = 15
        ID_dstE = 4
    # 未知指令，报错提醒
    else:
        # print("Decoding error: invalid instruction icode = %d, exit now" %ID_icode)
        sys.exit(0)
    return (ID_icode, ID_ifun, ID_valA, ID_valB, ID_valP, ID_valC, ID_rB, ID_rA, ID_dstE, ID_dstM)
#返回值均为int类型

# ID到EX段之间的流水线寄存器，接受EX_bubble信号，其有效时，寄存器给出一个气泡以刷新后面阶段的指令
def ID_EX(input, EX_bubble):
    # 产生nop指令对应的信号，以刷新后面的指令
    if EX_bubble == 1:
        return(1, 0, None, None, None, None, 15, 15, None, None)
    return input


def Execute(pre_signals):
    (ID_icode, ID_ifun, ID_valA, ID_valB, ID_valP, ID_valC, ID_rB, ID_rA, ID_dstE, ID_dstM) = pre_signals
    EX_valP = ID_valP; EX_valC = ID_valC; EX_icode = ID_icode; EX_ifun = ID_ifun; EX_valA = ID_valA; EX_rB = ID_rB; EX_rA = ID_rA; EX_dstE = ID_dstE; EX_dstM = ID_dstM

    # debug
    # print("EX_icode: %d" %EX_icode)

    if(EX_icode == 6):                             # OPq
        op = Resources.OP[EX_ifun]
        EX_valE = eval( str(ID_valB) + op + str(ID_valA) )


        # debug
        # print("ID_valB = %d, ID_valA = %d, EX_valE = %d" %(ID_valB, ID_valA, EX_valE))


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
        # print("Executing error: invalid instruction, exit now")
        sys.exit(0)
    return (EX_valE, EX_valP, EX_Cnd,  EX_valC, EX_icode, EX_ifun, EX_valA, EX_rB, EX_rA, EX_dstE, EX_dstM)


def Memory(pre_signals):
    (EX_valE, EX_valP, EX_Cnd,  EX_valC, EX_icode, EX_ifun, EX_valA, EX_rB, EX_rA, EX_dstE, EX_dstM) = pre_signals
    MEM_valP = EX_valP; MEM_Cnd = EX_Cnd; MEM_valC = EX_valC; MEM_icode = EX_icode; MEM_rB = EX_rB; MEM_valE = EX_valE; MEM_ifun = EX_ifun; MEM_rA = EX_rA; MEM_dstE = EX_dstE; MEM_dstM = EX_dstM

    # debug
    # print("MEM_icode: %d" %MEM_icode)

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
        # print("Memorying error: invalid instruction, exit now")
        sys.exit(0)
    return (MEM_valP, MEM_Cnd, MEM_valC, MEM_icode, MEM_valM, MEM_rB, MEM_valE, MEM_ifun, MEM_rA, MEM_dstE, MEM_dstM)

def WriteBack(pre_signals):     
    (MEM_valP, MEM_Cnd, MEM_valC, MEM_icode, MEM_valM, MEM_rB, MEM_valE, MEM_ifun, MEM_rA, MEM_dstE, MEM_dstM) = pre_signals
    WB_icode = MEM_icode; WB_ifun = MEM_ifun; WB_dstE = MEM_dstE; WB_dstM = MEM_dstM

    # debug
    # print("WB_icode: %d" %WB_icode)

    if(WB_icode == 6):                             #OPq

        # debug
        # print("MEM_rB = %d, MEM_valE = %d" %(MEM_rB, MEM_valE))


        Resources.reg[MEM_rB] = MEM_valE
    elif(WB_icode == 1):                           # nop
        pass
    elif(WB_icode == 2):                           #rrmovq and cmovxx
        if(MEM_Cnd == 1):
            Resources.reg[MEM_rB] = MEM_valE
    elif(WB_icode == 3 and WB_ifun == 0):             #irmovq
        Resources.reg[MEM_rB] = MEM_valE
    elif(WB_icode == 4 and WB_ifun == 0):             #rmmovq
        pass
    elif(WB_icode == 5 and WB_ifun == 0):             #mrmovq
        Resources.reg[MEM_rA] = MEM_valM
    elif(WB_icode == 10 and WB_ifun == 0):            #pushq
        Resources.reg[4] = MEM_valE
    elif(WB_icode == 11 and WB_ifun == 0):            #popq
        Resources.reg[4] = MEM_valE
        Resources.reg[MEM_rA] = MEM_valM  
    elif(WB_icode == 7):                           #jxx
        pass
    elif(WB_icode == 8):                           #call
        Resources.reg[4] = MEM_valE
    elif(WB_icode == 9):                           #ret
        Resources.reg[4] = MEM_valE
    # 未知指令，报错提醒
    else:
        # print("Writing back error: invalid instruction, exit now")
        sys.exit(0)
        
    return(WB_icode, WB_ifun, WB_dstE, WB_dstM)


# 冲突检测模块，用于产生阻塞和气泡的信号
def Hazard_Detection(HD_signals):
    (ID_rA, ID_rB, EX_dstM, EX_dstE, MEM_dstM, MEM_dstE, WB_dstM, WB_dstE, IF_icode, ID_icode, EX_icode, EX_cycles0) = HD_signals
    ID_stall = EX_bubble = IF_stall = IF_bubble = 0

    # IF_stall ID_stall EX_bubble信号处理数据冲突
    if (ID_rA == EX_dstM or ID_rA == EX_dstE or ID_rA == MEM_dstM or ID_rA == MEM_dstE or ID_rA == WB_dstM or ID_rA == WB_dstE) and (ID_rA != 15):
        ID_stall = EX_bubble = IF_stall = 1
        # print("1")
    if (ID_rB == EX_dstM or ID_rB == EX_dstE or ID_rB == MEM_dstM or ID_rB == MEM_dstE or ID_rB == WB_dstM or ID_rB == WB_dstE) and (ID_rB != 15):
        ID_stall = EX_bubble = IF_stall = 1
        # print("2")

    # IF_bubble信号处理ret指令的控制冲突
    if IF_icode == 9 or ID_icode == 9 or EX_icode == 9:
        IF_bubble = 1

    # IF_bubble信号同样处理jxx指令的控制冲突
    if IF_icode == 7 or ID_icode == 7:
        IF_bubble = 1 

    # IF_bubble信号同样处理EX多周期的问题
    if EX_cycles0 > 0:
        ID_stall = EX_bubble = IF_stall = 1

    return (IF_stall, ID_stall, EX_bubble, IF_bubble)
print("running")        