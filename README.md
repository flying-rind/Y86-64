# Y86-64指令模拟器
本模拟器采用PIPELINE形式模拟流水线周期处理器的执行，包含了以下主要程序和说明文档：
* Y86-64_Simulator_PIPE.py

    这是主程序，模拟指令集的运行。其读取COE格式的文件。每条指令执行后可以输出此时CPU的内存、寄存器、状态码、CPU状态等信息。关于流水线的冲突和结构的一些具体说明在[流水线说明](Y86-64指令模拟器说明.md)中

* Functions.py

    这个程序中定义了CPU的五个阶段，并包含了一些辅助的函数，包括从内存的指定位置读取固定字节或写入固定字节。

* Resource.py

    这个程序里只含了程序可见的状态，包括寄存器，条件码，内存，PC，程序状态等一些信息。同时为主存设计了一个Data Cache

* ISA/ISA.ipynb
   
   这个程序里是对采用的Y86的指令集的一些详细说明。包括了：
   * CPU各阶段说明
   * 指令编码
   * 指令各阶段微操作
  
* Test_Cache.py
    
    这个程序中，通过分块和不分块两种矩阵乘法访存方式对Cache命中率进行测试。一些详细的说明放在了[Cache说明](Cache说明.md)中。

* Vector_speedup.ipynb

    这个程序是通过一个循环对向量指令进行测试，具体的说明在[向量加速部件说明](使用向量部件加速循环.md)中找到

另外，Test文件夹内的coe文件都是对模拟器进行指令测试:
* add_100.coe文件实现1到100的加法。
* test_pipeline和test_pipeline2是对普通流水线（未处理任何冲突）的简单测试
* test_stall是测试数据相关（目前只通过stall解决）
* test_jump和test_ret对测试控制依赖的解决（通过插入nop指令解决）


目前开发进度：

- [x] 添加流水线寄存器
- [x] 解决数据相关
- [x] 解决控制相关
- [x] 为主存添加一个Cache
- [x] 为L1Cache添加写缓冲
- [x] 为L1Cache的写缓冲添加写合并功能
- [ ] 添加汇编器，这样我们能够写汇编代码而不是机器代码来对流水线进行测试
- [ ] 添加数据定向以提高性能