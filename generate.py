#! /usr/bin/env python3

import multiprocessing
import argparse
import sys
import os
import re
from typing import List

cpu_dir = "/sys/devices/system/cpu/"
sibling = "topology/thread_siblings_list"
topology = cpu_dir + "{}/"+ sibling

def generate(queues, cores : List[int], pin : bool) -> str:
  res = "Q {}".format(queues)
  fmt = ""
  if pin:
      fmt = "\ne {0} {1} 0\ns {0} {1} 0"
  else:
      fmt = "\ne -1 {1} 0\ns -1 {1} 0"
  for (i, c) in enumerate(cores):
      res += fmt.format(i, i % queues)
  return res

def main(argv : List[str]) -> int:
  cpu_count = multiprocessing.cpu_count()
  parser = argparse.ArgumentParser(description='Generating sgx-musl.conf')
  parser.add_argument("-n", type=int, default = cpu_count, help = "Number of cpus leave blank for max [On this machine: {}]".format(cpu_count))
  parser.add_argument("-ht", action="store_true", help="Use hyperthreads, if don't use hyperthreads n might not be reached")
  parser.add_argument("-q", type=int, default = -1, help = "Number of system call queues to use [default: -n]".format(cpu_count))
  parser.add_argument("-p", action="store_true", help="Pin threads to cores")
  parser.add_argument("CORE", type=int, nargs='*', help="Cores to use overrides -n and -ht")
  args = parser.parse_args(argv[1:])
  
  set_q = False
  if (args.q == -1):
      set_q = True
      args.q = args.n

  if (len(args.CORE) > 0):
      print(generate(args.q, args.CORE, args.p))
      return 0
  if (args.ht):
      print(generate(args.q, range(args.n), args.p))
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
  res.sort()
  if len(res) <= args.n:
      if (set_q):
          args.q = len(res)
      print(generate(args.q, res, args.p))
  else:
      print(generate(args.q, res[:args.n], args.p))

if __name__ == "__main__":
  exit(main(sys.argv))

