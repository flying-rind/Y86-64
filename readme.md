# Y86-64指令模拟器
本模拟器采用PIPELINE形式模拟流水线处理器的执行，包含了三个主要程序：
* Y86-64simulator_SEQ.ipynb

    这是主程序，模拟指令集的运行。其读取COE格式的文件。每条指令执行后可以输出此时CPU的内存、寄存器、状态码、CPU状态等信息。

* functions.py

    这个程序中定义了CPU的五个阶段，并包含了一些辅助的函数，包括从内存的指定位置读取固定字节或写入固定字节。

* resource.py

    这个程序里只包含了程序可见的状态，包括寄存器，条件码，内存，PC，程序状态等一些信息。

* ISA.ipynb
   
   这个程序里是对采用的Y86的指令集的一些详细说明。包括了：
   * CPU各阶段说明
   * 指令编码
   * 指令各阶段微操作
  

另外，文件夹内的coe文件都是对模拟器进行指令测试，其中add_100.coe文件实现1到100的加法。

test_pipeline.coe文件使用几条没有任何数据或者控制相关的简单指令对流水线进行测试。

目前开发进度：

- [x] 添加流水线寄存器
- [ ] 添加汇编器，这样我们能够写汇编代码而不是机器代码来对流水线进行测试
- [ ] 解决数据相关
- [ ] 解决控制相关
