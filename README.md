bigappleserialbus
=================

bus notifier for NYC MTA

for raspberry pi, but you could probably make it go on as a taskbar widget... 

lights up green when it's time to get ready to go, red when it's time to go.

uses OMG BIG DATA to predict when the bus is gonna come

![Picture of Big Apple Serial Bus](https://raw.githubusercontent.com/jeremybmerrill/bigappleserialbus/master/img/front-small.jpg)

install
-------

1. ssh to your pi
2. git clone https://github.com/jeremybmerrill/bigappleserialbus.git
3. `pip install -r requirements.txt`
3. get a BusTime API key from the MTA [here](https://spreadsheets.google.com/viewform?hl=en&formkey=dG9kcGIxRFpSS0NhQWM4UjA0V0VkNGc6MQ#gid=0)
4. create a file called apikey.txt that contains your API key, optionally followed by a newline.
5. create a file called config.yaml, modeled after config-example.yaml. 
6. get the GTFS stop identifier for your line from the [VehicleMonitoring](http://bustime.mta.info/wiki/Developers/SIRIVehicleMonitoring) API. (Literally watch the feed until a bus is at your stop, then record the stop identifier); paste that into the config file.
7. sudo python bigappleserialbus.py
8. to run on startup, add this line to `/etc/rc.local`: <pre>(sleep 10; python /home/pi/bigappleserialbus/bigappleserialbus.py)&</pre>

hardware
--------
512mb raspberry pi
latest raspbian
[AdaFruit Pi Cobbler](http://www.adafruit.com/products/914)
[AdaFruit's USB WiFi dongle](https://www.adafruit.com/products/814)
a breadboard
some LEDs
some wires

setup/circuit design
---------------
![Picture of Board](https://raw.githubusercontent.com/jeremybmerrill/bigappleserialbus/master/img/board-blurred-small.jpg)

for each bus line, wire up: 
a GPIO pin -> 300ishΩ LED -> 560Ω resistor -> gnd


when do lights go on?
----------------------

Imagine a timeline:
````
|---------------------------------------------|------------------|------|
A                     b                       C         d        E   f  G
````
a) Bus is 7 minutes away, plus walking time. Time to get think about leaving.<br>
b) Green light on<br>
c) Bus is 3 minutes away, plus walking time. Get your stuff and go.<br>
d) Red light on<br>
e) Time to leave. Go now!<br>
f) Red light off. You might not be able to make it, unless you run faster than your walking time.<br>
g) Bus passes your stop.<br>

Walking time is the sum of the time it takes to get out of your apartment to the street (constant per stop), and the amount of time it takes to get to any specific stop (which varies per stop, since some stops are farther from you than others).

Bus arrival times are predicted using k-means clustering -- that is, BIG DATA ANALYTICS AND MACHINE LEARNING -- to based on previous, similar bus trajectories collected while the script runs. Inspired by [this academic paper](http://www.iis.sinica.edu.tw/~cclljj/publication/2012/12_GIS-HTTP.pdf).

will this work in my city?
--------------------------
I dunno, maybe!

It'll probably work fine if your city uses the [SIRI](http://en.wikipedia.org/wiki/Service_Interface_for_Real_Time_Information) data standard. If you're not in New York and want to use bigappleserialbus, please send me a note, I'd be happy to work with you to extend the code to support your city.

can I help?
-----------
Yes. I would love to hear from you. Send me a note, open an issue or send a pull request. :)

ideas for later:
-----------------
1. Use the light sensor to dim/brighten the LEDs based on ambient light (so they're dim if the light is off).
1. Use the variable resistor/potentiometer to calibrate walking speed (e.g. it's easier to leave the house in the summer, or when no friends are here)
1. Blink the green LED to indicate time until next bus. (E.g. once per 20 seconds if bus is 20 minutes away, when bus is TimeToGo, turn on continuously)
1. Blink for 20 secs when it's really time to run.
1. use a shift register to support > 4 bus routes or use fewer GPIO ports

license
-------
all code except bigappleserialbus/kmodes.py is copyrighted, but licensed to you under the terms of the Apache license (see LICENSE). bigappleserialbus/kmodes.py is licensed under the MIT license (see bigappleserialbus/KMODES_LICENSE)