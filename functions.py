import resources

#从address处开始，取出numbers_of_bytes个字节,返回一个字符串
def Load_Memory(address, number_of_bytes):
    a = ''
    for i in range(0, number_of_bytes):
        a += resources.mem[address + i]
    return a

#从address处开始，将val的number_of_bytes个字节写入内存
def Store_Memory(address, number_of_bytes, val):

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
        resources.mem[address + i] = val[14 - 2*i] + val[15 - 2*i]


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

def Fetch():
    icode_ifun = Load_Memory(resources.PC, 1)
    icode = hex_2_dec(icode_ifun[0])
    ifun = hex_2_dec(icode_ifun[1])

    #debug here
    #print(icode_ifun, icode, ifun)

    #若为halt指令，直接返回
    if(icode == 0 or icode == 1 ):                             #halt or nop
        ifun = 0
        rA = 0
        rB = 0
        valP = resources.PC+1
        valC = 0
        if(icode == 0):
            resources.stat = 2
        return icode, ifun, rA, rB, valP, valC

    rA_rB = Load_Memory(resources.PC+1, 1)
    rA = hex_2_dec(rA_rB[0])
    rB = hex_2_dec(rA_rB[1])    
    if(icode == 6):                             #OPq
        valP = resources.PC + 2
        valC = 0
    elif(icode == 2):                           #rrmovq and cmovxx
        valP = resources.PC + 2
        valC = 0
    elif(icode == 3 and ifun == 0):             #irmovq
        valC = hex_2_dec(Load_Memory(resources.PC+2, 8))
        valP = resources.PC + 10
    elif(icode == 4 and ifun == 0):             #rmmovq
        valC = hex_2_dec(Load_Memory(resources.PC+2, 8))
        valP = resources.PC + 10
    elif(icode == 5 and ifun == 0):             #mrmovq
        valC = hex_2_dec(Load_Memory(resources.PC+2, 8))  
        valP = resources.PC + 10
    elif(icode == 10 and ifun == 0):            #pushq
        valP = resources.PC + 2
        valC = 0
    elif(icode == 11 and ifun == 0):            #popq
        valP = resources.PC + 2
        valC = 0
    elif(icode == 7):                           #jxx
        valP = resources.PC + 9
        valC = hex_2_dec(Load_Memory(resources.PC + 1, 8))
    elif(icode == 8):                           #call
        valC = hex_2_dec(Load_Memory(resources.PC + 1, 8))
        valP = resources.PC + 9
    elif(icode == 9):                           #ret
        valP = resources.PC + 1
        valC = 0
    return icode, ifun, rA, rB, valP, valC
#返回值类型均为int

def Decode(rA, rB, icode, ifun):
    if(icode == 6):                             #OPq
        valA = resources.reg[rA]
        valB = resources.reg[rB]
    elif(icode == 2):                           #rrmovq and cmovxx
        valA = resources.reg[rA]
        valB = 0
    elif(icode == 3 and ifun == 0):             #irmovq
        valA = resources.reg[rA]
        valB = resources.reg[rB]
    elif(icode == 4 and ifun == 0):             #rmmovq
        valA = resources.reg[rA]
        valB = resources.reg[rB]
    elif(icode == 5 and ifun == 0):             #mrmovq
        valA = resources.reg[rA]
        valB = resources.reg[rB]
    elif(icode == 10 and ifun == 0):            #pushq
        valA = resources.reg[rA]
        valB = resources.reg[4]
    elif(icode == 11 and ifun == 0):            #popq
        valA = resources.reg[4]
        valB = resources.reg[4]
    elif(icode == 7):                           #jxx
        valA = 0
        valB = 0
    elif(icode == 8):                           #call
        valA = 0
        valB = resources.reg[4]
    elif(icode == 9):                           #ret
        valA = resources.reg[4]
        valB = resources.reg[4]
    elif(icode == 1):                           #nop
        valA = 0
        valB = 0
    return valA, valB
#返回值均为int类型

def Execute(valA, valB, icode, ifun, valC):
    if(icode == 6):                             #OPq
        op = resources.OP[ifun]
        valE = eval( str(valB) + op + str(valA) )
        set_CC(valE)
        Cnd = 0
    elif(icode == 2):                           #rrmovq and cmovxx
        valE = 0 + valA
        Cnd = Cond(ifun)
    elif(icode == 3 and ifun == 0):             #irmovq
        valE = 0 + valC
        Cnd = 0
    elif(icode == 4 and ifun == 0):             #rmmovq
        valE = valB + valC
        Cnd = 0
    elif(icode == 5 and ifun == 0):             #mrmovq
        valE = valB + valC
        Cnd = 0          
    elif(icode == 10 and ifun == 0):            #pushq
        valE = valB - 8
        Cnd = 0
    elif(icode == 11 and ifun == 0):            #popq
        valE = valB + 8
        Cnd = 0
    elif(icode == 7):                           #jxx
        valE = 0
        Cnd = Cond(ifun)
    elif(icode == 8):                           #call
        valE = valB - 8
        Cnd = 0
    elif(icode == 9):                           #ret
        valE = valB + 8
        Cnd = 0
    elif(icode == 1):                           #nop
        valE = 0
        Cnd = 0
    return valE, Cnd

def Memory(valA, valE, icode, ifun, valP):
    if(icode == 6):                             #OPq
        valM = 0
    elif(icode == 2):                           #rrmovq and cmovxx
        valM = 0
    elif(icode == 3 and ifun == 0):             #irmovq
        valM = 0
    elif(icode == 4 and ifun == 0):             #rmmovq
        Store_Memory(valE, 8, valA)
        valM = 0
    elif(icode == 5 and ifun == 0):             #mrmovq
        valM = hex_2_dec(Load_Memory(valE, 8))
    elif(icode == 10 and ifun == 0):            #pushq
        Store_Memory(valE, 8, valA)
        valM = 0
    elif(icode == 11 and ifun == 0):            #popq
        valM = hex_2_dec(Load_Memory(valA, 8))
    elif(icode == 7):                           #jxx
        valM = 0
    elif(icode == 8):                           #call
        Store_Memory(valE, 8, valP)
        valM = 0
    elif(icode == 9):                           #ret
        valM = hex_2_dec(Load_Memory(valA, 8))
    elif(icode == 1):                           #nop
        valM = 0
    return valM

def WriteBack(rB, valE, icode, ifun, valM, rA, Cnd):          
    if(icode == 6):                             #OPq
        resources.reg[rB] = valE
    elif(icode == 2):                           #rrmovq and cmovxx
        if(Cnd == 1):
            resources.reg[rB] = valE
    elif(icode == 3 and ifun == 0):             #irmovq
        resources.reg[rB] = valE
    elif(icode == 4 and ifun == 0):             #rmmovq
        pass
    elif(icode == 5 and ifun == 0):             #mrmovq
        resources.reg[rA] = valM
    elif(icode == 10 and ifun == 0):            #pushq
        resources.reg[4] = valE
    elif(icode == 11 and ifun == 0):            #popq
        resources.reg[4] = valE
        resources.reg[rA] = valM  
    elif(icode == 7):                           #jxx
        pass
    elif(icode == 8):                           #call
        resources.reg[4] = valE
    elif(icode == 9):                           #ret
        resources.reg[4] = valE
    elif(icode == 1):                           #nop
        pass
    return

def Compute_Next_PC(valP, Cnd, valC, icode, valM):
    if(icode == 7):                            #jxx
        if(Cnd == 1):
            resources.PC =  valC
        else:
            resources.PC = valP
    elif(icode == 9):                           #ret
        resources.PC = valM
    else:
        resources.PC = valP
    return resources.PC

print("running")