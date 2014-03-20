bigappleserialbus
=================

hardware bus notifier for NYC MTA

install
-------

1. ssh to your pi
2. git clone https://github.com/jeremybmerrill/bigappleserialbus.git
3. sudo pip install pyyaml # you might need to `sudo apt-get install python-pip`
3. get a BusTime API key from the MTA [here](https://spreadsheets.google.com/viewform?hl=en&formkey=dG9kcGIxRFpSS0NhQWM4UjA0V0VkNGc6MQ#gid=0)
4. create a file called apikey.txt that contains your API key, optionally followed by a newline.
5. create a file called config.yaml, modeled after config-example.yaml. 
6. get the GTFS stop identifier for your line from the [VehicleMonitoring](http://bustime.mta.info/wiki/Developers/SIRIVehicleMonitoring) API. (Literally watch the feed until a bus is at your stop, then record the stop identifier); paste that into the config file.
7. sudo python bigappleserialbus.py

platform
--------
512mb raspberry pi
latest raspbian
[AdaFruit Pi Cobbler](http://www.adafruit.com/products/914)
[AdaFruit's USB WiFi dongle](https://www.adafruit.com/products/814)
a breadboard, some LEDs and wires

circuit design
---------------
I'll make a picture later.
it's just pin -> resistor -> LED -> gnd, twice per bus line.

when do lights go on?
----------------------

Imagine a timeline:
````
|---------------------------------------------|------------------|------|
A                     b                       C         d        E   f  G
````
a) Bus is 7 minutes away, plus walking time. Time to get think about leaving.
b) Green light on
c) Bus is 3 minutes away, plus walking time. Get your stuff and go.
d) Red light on
e) Time to leave. Go now!
f) Red light off. You might not be able to make it, unless you run faster than your walking time.
g) Bus passes your stop.

Walking time is the sum of the time it takes to get out of your apartment to the street (constant per stop), and the amount of time it takes to get to any specific stop (which varies per stop, since some stops are farther from you than others).

Ideas for later:
-----------------
1. Use the light sensor to dim/brighten the LEDs based on ambient light (so they're dim if the light is off).
1. Use the variable resistor/potentiometer to calibrate walking speed (e.g. it's easier to leave the house in the summer, or when no one is here)
1. Blink the green LED to indicate time until next bus. (E.g. once per 20 seconds if bus is 20 minutes away, when bus is TimeToGo, turn on continuously)
1. Use 3x buttons to indicate which bus I want to take, so piezo buzzer plays a tune when it's time to go when that particular bus is close.
