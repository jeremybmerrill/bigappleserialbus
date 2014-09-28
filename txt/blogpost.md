Never Miss the Bus with Big Apple Serial Bus -- Ambient Bus Notifications for Raspberry Pi


Every Sunday, I meet some friends at a bar in Boerum Hill for pub trivia. I've gone regularly for about two years and have come to recognize a lot of the folks on other teams and see them around. And it's a good way to transition from the weekend to the workweek. It's a little like church for secular, beer nerd, regular-nerd folk in Brooklyn, I sometimes think.

On a beautiful evening, the bar is a nice twenty minute stroll away, on a quiet street lined by trees and brownstones. If it's cold or raining, it's a slog. But even without the fear of damnation to enforce attendence, I still try to go almost every week. So when the weather's bad, I take the bus.

I also take the bus on one of four lines to Trader Joe's or if I'm meeting friends in Williamsburg. For trips that aren't walkable, but aren't conveniently accessible by subway, the bus is terrific -- when it comes. Buses on these lines come only every 30 minutes on Sunday evenings when I'm going to the bar, and as rarely as every hour on Saturday or Sunday nights. 

With this bus frequency, missing the bus can be a real pain. 

In April 2014, New York's MTA launched the [bustime](http://bustime.mta.info) system to provide real-time bus location information. It has a decent mobile app but checking my phone or a computer every few minutes when it's time to leave to see when to catch the bus is a pain. Luckily, it also has an API, allowing computer programs to access that data. So I built bigappleserialbus, a hardware bus notifier that uses little lights to tell me when to get ready to go and when to run out the door to catch the bus.

I can tell literally _at a glance_ if my bus is close.

The bigappleserialbus system keeps track of each bus that's on its way to my stop and stores them in a database. It uses the k-means machine learning algorithm to predict, based on the past saved trajectories, to predict when the next bus will arrive at my stop. When it's time to get ready, the green light goes on. Time to go, red light. 

The ambient notifications component of Big Apple Serial Bus is a first draft of an important design consideration for the "internet of things". Too many devices beep to get their user's attention, making the tool useless -- we've all had the experience of hearing an occasional beep and wondering if it's coming from the smoke alarm or the microwave or the dishwasher or the washing machine or the refrigerator... This sort of distracting, audible notification only makes sense for truly time-sensitive events, like a phone call or an open refrigerator door. Events that only sometimes require immediate action, like the Big apple Serial Bus, have to be less obtrusive, but still easily legible. The lights accomplish this: they're not distracting when I don't care, and they're easy to interpret when I do.

A better version of this tool would not require the user to memorize a list of bus routes from left to right, perhaps by having cutouts of the route names that light up. I don't have that kind of machining skill though.

I want this to be available to other people, so please let me know if you're interested. I want to hear from you. Right now, you need some very basic hardware hacking experience (really basic, like putting wires in a breadboard; no soldering), Python installation skills and at least some comfort editing config files. The full instructions are [here](https://github.com/jeremybmerrill/bigappleserialbus/blob/master/README.md).

I've been thinking about a web interface for initial setup: a place to tell Big Apple Serial Bus which bus routes you care about and what stop is nearest to your apartment. If other cities use the same [SIRI](http://en.wikipedia.org/wiki/Service_Interface_for_Real_Time_Information) format, that could be supported too. 
