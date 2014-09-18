#!/usr/bin/env python

__author__ = 'Jeremy B. Merrill'
__email__ = 'jeremybmerrill@gmail.com'
__license__ = 'Apache'
__version__ = '0.1'

import subprocess 

def is_on_pi():
  uname_m = subprocess.Popen(["uname", "-m"], stdout = subprocess.PIPE, stderr = subprocess.STDOUT).communicate()[0]
  return uname_m.strip() == "armv6l"
