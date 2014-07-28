import RPi.GPIO as GPIO

class Light:
  def __init__(self, pin):
    self.pin = pin
    self.status = False
    GPIO.setup(pin, GPIO.OUT)

  def toggle(self):
    self.status = not self.status
    self.do()

  def on(self):
    self.status = True
    self.do()

  def off(self):
    self.status = False
    self.do()

  def do(self):
    GPIO.output(light.pin, light.status)
    if light.status:
      logging.debug("illuminating pin #%(pinNum)d" % {'pinNum': light.pin})
