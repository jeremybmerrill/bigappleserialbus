import subprocess 

def is_on_pi():
  uname_m = subprocess.Popen(["uname", "-m"], stdout = subprocess.PIPE, stderr = subprocess.STDOUT).communicate()[0]
  return uname_m.strip() == "armv6l"
