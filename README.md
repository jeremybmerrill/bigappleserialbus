bigappleserialbus
=================

hardware bus notifier for NYC MTA

lights up green when it's time to get ready to go, green when it's time to go.

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
8. to run on startup, add this line to `/etc/rc.local`: <pre>(sleep 10; python /home/pi/bigappleserialbus/bigappleserialbus.py)&</pre>

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
it's just pin -> LED -> 560Ω resistor -> gnd, twice per bus line.

If you have 'em, probably better to use a resistor with a lower resistance, like 300ish, I think?

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

Ideas for later:
-----------------
1. Use the light sensor to dim/brighten the LEDs based on ambient light (so they're dim if the light is off).
1. Use the variable resistor/potentiometer to calibrate walking speed (e.g. it's easier to leave the house in the summer, or when no friends are here)
1. Blink the green LED to indicate time until next bus. (E.g. once per 20 seconds if bus is 20 minutes away, when bus is TimeToGo, turn on continuously)
1. Blink for 20 secs when it's really time to run.
1. Keep track of average time to "home" stop for each preceding stop. Constrain speed estimates to 80th or 90th percentile (to avoid erroneous lights when the bus is going really fast for a short stretch)
1. For each stop S, keep track of the distribution of times it took for a bus at S to arrive at the "home" stop. Also keep track of distribution of time to home from S over a bucketized amount of time for the bus to travel some other constant distance (maybe from when it departed terminal? to account for variances in speed over date/time/weather)