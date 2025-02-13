import m5
from m5.objects import *

import argparse

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

## Add the "binary" option to the script
DEFAULT_BINARY = '/u/csc368h/winter/pub/workloads/hello'

## Command line args
parser = argparse.ArgumentParser()
parser.add_argument(
    'binary',
    type=str,
    default=DEFAULT_BINARY,
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

## Parse command-line arguments
args = parser.parse_args()

# System creation
system = System()

## gem5 needs to know the clock and voltage
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = args.frequency
system.clk_domain.voltage_domain = VoltageDomain() # defaults to 1V

## Create a crossbar so that we can connect main memory and the CPU (below)
system.membus = SystemXBar()
system.system_port = system.membus.cpu_side_ports

## Use timing mode for memory modelling
system.mem_mode = 'timing'

# CPU Setup
system.cpu = X86O3CPU() if args.cpu_type == 'o3' else X86MinorCPU()

## This is needed when we use x86 CPUs
system.cpu.createInterruptController()
system.cpu.interrupts[0].pio = system.membus.mem_side_ports
system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
system.cpu.interrupts[0].int_responder = system.membus.mem_side_ports

# L1 data and instruction cache setups
system.cpu.l1d = L1DCache(size=args.l1d_size)
system.cpu.l1i = L1ICache(size=args.l1i_size)

system.l2_bus = L2XBar(width=64) # may wish to increase to that it equals or matches with cache line size (which is 64)

system.cpu.l1d.cpu_side = system.cpu.dcache_port
system.cpu.l1i.cpu_side = system.cpu.icache_port
system.cpu.l1d.mem_side = system.l2_bus.cpu_side_ports
system.cpu.l1i.mem_side = system.l2_bus.cpu_side_ports

# L2 cache setup
system.l2_cache = L2Cache(size=args.l2_size)
system.l2_cache.mem_side = system.membus.cpu_side_ports
system.l2_cache.cpu_side = system.l2_bus.mem_side_ports

# Memory setup
system.mem_ctrl = MemCtrl()
system.mem_ctrl.port = system.membus.mem_side_ports

## A memory controller interfaces with main memory; create it here
system.mem_ctrl.dram = DDR3_1600_8x8()

## A DDR3_1600_8x8 has 8GB of memory, so setup an 8 GB address range
address_ranges = [AddrRange('8GB')]
system.mem_ranges = address_ranges
system.mem_ctrl.dram.range = address_ranges[0]

# Process setup
process = Process()

## Use a full path to the binary
binary = args.binary
# process.cmd = [binary, args.binary_args] # for minor
process.cmd = [binary] + args.binary_args.split() # for O3

## The necessary gem5 calls to initialize the workload and its threads
system.workload = SEWorkload.init_compatible(binary)
system.cpu.workload = process
system.cpu.createThreads()

# Start the simulation
root = Root(full_system=False, system=system) # must assign a root

m5.instantiate() # must be called before m5.simulate

print("**** Starting gem5 simulation with caches ****")
exit_event = m5.simulate()
print("**** Exited @ tick {} because {} ****".format(
    m5.curTick(), exit_event.getCause()
))