from subprocess import call

def onPi():
  uname_m = call(["uname", "-m"])
  return uname_m == "armv6l"