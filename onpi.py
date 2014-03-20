import subprocess 

def onPi():
  uname_m = subprocess.Popen(["uname", "-m"], stdout = subprocess.PIPE, stderr = subprocess.STDOUT).communicate()[0]
  return uname_m == "armv6l"
