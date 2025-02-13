import m5
from m5.objects import *
import argparse

#
# L1 I/D Cache & L2 Cache class
#
class L1ICache(Cache):
    assoc = 2
    tag_latency = 2
    data_latency = 2
    response_latency = 2
    mshrs = 4
    tgts_per_mshr = 20
    size = '32kB'
    is_read_only = True
    writeback_clean = True

class L1DCache(Cache):
    assoc = 2
    tag_latency = 2
    data_latency = 2
    response_latency = 2
    mshrs = 4
    tgts_per_mshr = 20
    size = '32kB'
    writeback_clean = True

class L2Cache(Cache):
    assoc = 8
    tag_latency = 20
    data_latency = 20
    response_latency = 20
    mshrs = 20
    tgts_per_mshr = 12
    size = '256kB'
    writeback_clean = True

#
# command line argument
#
parser = argparse.ArgumentParser()
parser.add_argument(
    'binary',
    type=str,
    help="Full path to the benchmark executable."
)
parser.add_argument(
    '-a', '--binary_args',
    type=str,
    default="",
    help="Arguments for the benchmark."
)
parser.add_argument(
    '-f', '--frequency',
    type=str,
    default='2GHz',
    help="Clock frequency for the CPU (default: 2GHz)."
)
parser.add_argument(
    '-c', '--cpu_type',
    type=str,
    default='o3',
    choices=['o3', 'minor'],
    help="CPU model: 'o3' for out-of-order, 'minor' for in-order."
)
parser.add_argument(
    '--l1i_size', type=str, default='32kB', help="L1 ICache size (e.g. 16kB, 32kB...)"
)
parser.add_argument(
    '--l1d_size', type=str, default='32kB', help="L1 DCache size"
)
parser.add_argument(
    '--l2_size', type=str, default='256kB', help="L2 cache size"
)
args = parser.parse_args()

#
# 创建 System
#
system = System()
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = args.frequency
system.clk_domain.voltage_domain = VoltageDomain()  # 默认1V

# 使用 timing mode 模拟时间
system.mem_mode = 'timing'

# 建立总线 (membus)，将来把 L2 与内存控制器挂接上
system.membus = SystemXBar()
system.system_port = system.membus.cpu_side_ports

#
# 选 CPU 类型
#
if args.cpu_type == 'o3':
    system.cpu = X86O3CPU()
else:
    system.cpu = X86MinorCPU()
    # 可以在此自定义 minorCPU 的 pipeline 宽度等，如:
    # system.cpu.executeInputWidth = 1
    # system.cpu.executeIssueLimit = 1

#
# 创建 L1 I/D cache，接在 CPU 和 L2 之间
#
system.cpu.icache = L1ICache(size=args.l1i_size)
system.cpu.dcache = L1DCache(size=args.l1d_size)

# 创建一个总线，用于连接 L1 和 L2
system.l1bus = L2XBar()

# 连接 L1I / L1D
system.cpu.icache.cpu_side = system.cpu.icache_port
system.cpu.dcache.cpu_side = system.cpu.dcache_port
system.cpu.icache.mem_side = system.l1bus.slave
system.cpu.dcache.mem_side = system.l1bus.slave

#
# 创建 L2，连接到 L1总线 和 主内存总线
#
system.l2cache = L2Cache(size=args.l2_size)
system.l2cache.cpu_side = system.l1bus.master
system.l2cache.mem_side = system.membus.cpu_side_ports

#
# 生成中断控制器(对 X86 CPU 必需)
#
system.cpu.createInterruptController()
system.cpu.interrupts[0].pio = system.membus.mem_side_ports
system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
system.cpu.interrupts[0].int_responder = system.membus.cpu_side_ports

#
# 内存控制器
#
system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()

# DDR3_1600_8x8 default 8GB
system.mem_ranges = [AddrRange('8GB')]
system.mem_ctrl.dram.range = system.mem_ranges[0]

# 将内存控制器端口挂载到 membus
system.mem_ctrl.port = system.membus.mem_side_ports

#
# 设置要运行的进程 (Syscall Emulation 模式)
#
process = Process()
binary = args.binary
binary_args = args.binary_args.split() if args.binary_args else []
process.cmd = [binary] + binary_args

system.workload = SEWorkload.init_compatible(binary)
system.cpu.workload = process
system.cpu.createThreads()

#
# 实例化并开始模拟
#
root = Root(full_system=False, system=system)
m5.instantiate()

print("**** Starting gem5 simulation with caches ****")
exit_event = m5.simulate()
print("**** Exited @ tick {} because {} ****".format(
    m5.curTick(), exit_event.getCause()
))
