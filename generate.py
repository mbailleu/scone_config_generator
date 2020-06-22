#! /usr/bin/env python3

import multiprocessing
import argparse
import sys
import os
import re
from typing import List, Tuple

cpu_dir = "/sys/devices/system/cpu/"
sibling = "topology/thread_siblings_list"
topology = cpu_dir + "{}/"+ sibling

Units = {
    "k"   : 10 ** 3,
    "M"   : 10 ** 6,
    "G"   : 10 ** 9,
    "E"   : 10 ** 12,
    "ki"  : 2 ** 10,
    "Mi"  : 2 ** 20,
    "Gi"  : 2 ** 30,
    "kB"  : 2 ** 10,
    "MB"  : 2 ** 20,
    "GB"  : 2 ** 30,
    "kiB" : 2 ** 10,
    "MiB" : 2 ** 20,
    "GiB" : 2 ** 30,
}

def add_threads(thread_type : str, queues : int, cores : List[int], pin : bool) -> str:
  res = ""
  fmt = "\n{0} {1} {2} 0"
  for i, c in enumerate(cores):
    res += fmt.format(thread_type, c if pin else -1, i % queues)
  return res

def to_base_number(number : str) -> int:
  match = re.search("\D+", number)
  if match == None:
    return int(number)
  digits = number[:match.start()]
  unit = number[match.start():]
  print(digits, unit)
  return int(digits) * Units.get(unit, 1)

def generate(queues : int, s_cores : List[int], e_cores : List[int], args) -> str:
  if queues > len(s_cores):
    print("You setting up more queues ({}) as you have outside threads ({}) working on them.".format(queues, len(s_cores)), file=sys.stderr)  

  if queues > len(e_cores):
    print("You setting up more queues ({}) as you have inside threads ({}) working on them.".format(queues, len(e_cores)), file=sys.stderr)  

  res = "Q {}".format(queues)
  if args.heap != "":
    res += "\nH {}".format(to_base_number(args.heap))
  if args.spins != "":
    res += "\nP {}".format(to_base_number(args.spins))
  if args.sleep != "":
    res += "\nL {}".format(to_base_number(args.sleep))
  res += add_threads('s', queues, s_cores, args.pin)
  res += add_threads('e', queues, e_cores, args.pin)
  return res

def distribute_cores(cores : List[int], s : int, e : int) -> Tuple[List[int],List[int]]:
  cores.sort()
  s_cores = cores[::2]
  e_cores = cores[1::2]
  e_cores += s_cores[s:]
  s_cores += e_cores[e:]
  s_cores = s_cores[:s]
  e_cores = e_cores[:e]
  e_cores.sort()
  s_cores.sort()
  return (s_cores, e_cores)

def main(argv : List[str]) -> int:
  cpu_count = multiprocessing.cpu_count()
  parser = argparse.ArgumentParser(description='Generating sgx-musl.conf')
  parser.add_argument("-n", type=int, default = -1, help = "Number of cpus leave blank for max [On this machine: {}]".format(cpu_count))
  parser.add_argument("-s", type=int, default = -1, help = "Number of outside threads [Default: {}]".format(cpu_count // 2))
  parser.add_argument("-e", type=int, default = -1, help = "Number of inside threads [Default: {}]".format(cpu_count // 2))
  parser.add_argument("-ht", action="store_true", help="Use hyperthreads, if not set N, S and E might not be reached")
  parser.add_argument("-q", type=int, default = -1, help = "Number of system call queues to use [default: S]".format(cpu_count/2))
  parser.add_argument("--pin", action="store_true", help="Pin threads to cores (experimental)")
  parser.add_argument("--heap", type=str, default = "", help = "Number of bytes for the heap support units (kiB, MiB, GiB)")
  parser.add_argument("--spins", type=str, default = "", help = "Number of spins before going to sleep for inside threads (supports suffix k, M, G, E)")
  parser.add_argument("--sleep", type=str, default = "", help = "How fast the amount of time, a thread sleeps increases (supports suffix k, M, G,E)")
  parser.add_argument("CORE", type=int, nargs='*', help="Cores to use overrides: --pin and -ht")
  args = parser.parse_args(argv[1:])
  
  if args.n == -1:
    args.n = cpu_count

  if args.s == -1:
    if args.e != -1:
      args.s = args.n - 1
    else:
      args.s = args.n // 2

  if args.e == -1:
    args.e = args.n - args.s

  set_q = False
  if (args.q == -1):
    set_q = True
    args.q = args.s

  if (args.e + args.s) > cpu_count:
    print("The computer has {} cores. You are trying to schedule more threads. Your setting is {} outside threads and {} inside threads. Use option -ht to ignore it.".format(cpu_count, args.s, args.e), file=sys.stderr)

  if (len(args.CORE) > 0):
    args.pin = True
    args.ht = True
    s_cores, e_cores = distribute_cores(args.CORE, args.s, args.e)
    print(generate(args.q, s_cores, e_cores, args))
    return 0
  if (args.ht):
    s_cores, e_cores = distribute_cores(list(range(args.s + args.e)), args.s, args.e)
    print(generate(args.q, s_cores, e_cores, args))
    return 0

  files = [topology.format(f) for f in os.listdir(cpu_dir) if re.match(r'cpu[0-9]+', f)]
  non_sibling = []
  for cpu in files:
    with open(cpu, "r") as c:
      val = c.read()
      if not val in non_sibling:
        non_sibling.append(val)

  res = []
  for cpu in non_sibling:
    res.append(int(cpu.split(',')[0]))

  s_cores, e_cores = distribute_cores(res, args.s, args.e)

  if len(res) <= args.s + args.e:
    if (set_q):
      args.q = min(len(s_cores), len(e_cores))
    #TODO correct args.s and args.e
    print(generate(args.q, s_cores, e_cores, args))
  else:
    print(generate(args.q, s_cores, e_cores, args))
  return 0

if __name__ == "__main__":
  exit(main(sys.argv))

