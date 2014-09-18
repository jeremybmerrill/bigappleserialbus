#!/usr/bin/env python

__author__ = 'Jeremy B. Merrill'
__email__ = 'jeremybmerrill@gmail.com'
__license__ = 'Apache'
__version__ = '0.1'

import RPi.GPIO as GPIO
import logging #magically the same as the one in bigappleserialbus.py

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
    GPIO.output(self.pin, self.status)
    if self.status:
      logging.debug("illuminating pin #%(pinNum)d" % {'pinNum': self.pin})
