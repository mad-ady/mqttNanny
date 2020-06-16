# mqttNanny
Provide time-based access to a linux desktop system for kids, cutting access when time runs out, keeping an eye on foreground programs

The code is a Python 3 script that runs as a daemon. It has two operation modes - local and remote. It starts in local mode when it can't connect to a MQTT broker. In this mode it loads its limits from a file and is less flexible. When running in remote mode it gets the allowance for the current user from a MQTT broker and allows the parent to control (and follow what the user is doing) dynamically. Basically, remote mode offers all the features, while local mode is a fallback in case of connectivity issues.
The main program loop runs every minute and gathers (and reports) information:
* what is the active TTY?
* what user is logged in using X11 in the current TTY?
* is the screensaver running?
* what is the active application title?

For the currently logged in user a counter is decremented every minute while the screensaver is not running. There are some notifications sent to the user (via notify-send and audible) when there's 10/5/1 minutes left. When time runs out, the screensaver is enabled and the user account is disabled (makes password login fail). Should the screensaver fail to enable 5 times in a row, the system is shutdown instead. Once allowance is greater than zero, the daemon restores the password of that account.

MQTT gives you the ability to see the collected data, to change the allowance for each user and also to request screenshots of the user's desktop session.

You may need to integrate it with MQTT and HomeAssistant (for best results). The full integration is out of scope of this readme.

# Installation and configuration
You can download and install the code from my github page:
```
$ sudo apt-get install git
$ cd /usr/local/share
$ sudo git clone https://github.com/mad-ady/mqttNanny.git
$ cd mqttNanny
$ sudo cp mqttNanny.yaml /etc/mqttNanny.yaml
$ sudo cp mqttNanny.service /etc/systemd/system/mqttNanny.service
```
You will need to install some dependencies as well:
```
$ sudo apt-get install python3-pip python3-yaml python3-notify2 espeak xscreensaver xdotool imagemagick
$ sudo pip3 install paho-mqtt
```
Note that currently only Linux systems are supported, but the code is written so that it could be extended for other OSes as well (pull requests are welcome). The linux system needs to be running Xorg (Xwayland probably needs many changes) and the screensaver program needs to be Xscreensaver or mate-screensaver. Support for other screensavers could be added in the future though (pull request welcome). The code was tested on a Odroid H2 (x86_64), Odroid XU4 (armhf) and an Odroid N2 (arm64). To migrate from mate-screensaver to xscreensaver you can do the following:
```
$ sudo apt-get purge mate-screensaver
$ xscreensaver-demo
```
While running xscreensaver-demo you can select which screensavers you want to use and also enable "Lock screen after" option to force it to ask for a password. You will need to make the desktop environment start the screensaver automatically by copying it to the autostart folder:
```
$ mkdir ~/.config/autostart
$ cp /usr/share/applications/xscreensaver-properties.desktop ~/.config/autostart/
$ sed -i 's/xscreensaver-demo/xscreensaver/' ~/.config/autostart/xscreensaver-properties.desktop
```
Also, make sure the system time is set correctly at boot (either via a RTC, NTP or fake-hwclock), otherwise local mode timekeeping won't work correctly.

You'll need to edit the configuration (/etc/mqttNanny.yaml) and set your relevant defaults. Make sure indenting is correct in the file (you can validate it with http://www.yamllint.com/), otherwise the program will fail to start. The options available are described below:
```
mqttServer - the ip/dns name of your MQTT broker
mqttPort - the TCP port your broker runs on (default is 1883)
mqttUser/mqttPass - your mqtt credentials. If your broker doesn't use authentication, simply omit the lines
baseTopic - a prefix used to build the topics used to send/receive messages. I personally use ha/<computer-name>/
mqttTimeTopicSuffix - the time remaining for each user will be transmitted in a topic built from <baseTopic>/<username>/<mqttTimeTopicSuffix>. In my case it's something like ha/pc/odroid/timeRemaining
mqttScreenshot - the topic where you want to receive screenshot images (MQTT can transport binary data as well)
mqttScreenshotCommand - the topic where you can request screenshots or not. This can be mapped to a switch in Home Assistant to toggle screenshots on or off.
mqttScreenshotDuration - how long until the screenshot feature turns itself off. If you want it always on, set it to 0
mqttScreenshotInterval - how often (in seconds) should it grab screenshots
screenshotHeight - resize the screenshot to this height (keeping aspect ratio), for efficiency reasons
screensaver - mate-screensaver or xscreensaver
graceTime - on startup, give graceTime minutes by default, if the current allowence is below this limit
whitelist - list of window title names for foreground apps that you don't want to consume the kid's time (e.g. Zoom, etc)
checkInterval - how often should the script's internal clock tick. 60 seconds means that allowance is checked every minute. You also get application changes every minute.
externalNotify - should either be False or point to a program/script that takes a string as argument and sends the message to you. For instance, I set it up to /usr/local/bin/telegram-send and get notified of events through a telegram bot.
no-signal - should point to an image file that is displayed when screenshots are turned off
users - contains a list of users to monitor. If a user which is not on the list logs in, their time is not managed, but data about their session and screenshots still get reported via MQTT.
defaultOfflineTime - how many minutes the user gets at program startup in case the program runs in local mode, without a connection to the MQTT broker. In case a file with the user's current allowance is found in /usr/local/share/mqttNanny/<username>/<date>, that value is loaded instead. That file is updated on every allowance change/decrease. 
```

For security, make the configuration file readable only by root:
```
$ sudo chown root:root /etc/mqttNanny.yaml
$ sudo chmod 400 /etc/mqttNanny.yaml
```
A service file can be used to control the daemon:
```
$ cat /etc/systemd/system/mqttNanny.service                                              
[Unit]
Description=mqttNanny
After=network.target
[Service]
ExecStart=/usr/local/share/mqttNanny/mqttNanny.py
Type=simple
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
$ sudo systemctl enable mqttNanny
$ sudo systemctl start mqttNanny
```
You can follow logs to troubleshoot by running:
```
$ sudo journalctl -f -u mqttNanny
```

# Home Assistant integration

Once mqttNanny is running on the target computer it is nice to be able to control it from a nice web interface. I found Home Assistant to be the perfect interface for Home Automation and custom/DIY scripts.

We'll be adding a few components to Home Assistant's configuration.yaml that will communicate with the script via MQTT. Consult the appropriate component documentation for more details.

```
camera:
  - platform: mqtt
    name: N2-PC Display
    topic: 'ha/pc/screenshot'

switch:
  - platform: mqtt
    command_topic: 'ha/pc/screenshot/command'
    state_topic: 'ha/pc/screenshot/command'
    payload_on: 'enable'
    payload_off: 'disable'
    name: N2-PC Enable screenshot
    retain: true

sensor:
  - platform: mqtt
    state_topic: 'ha/pc/activeUser'
    name: N2 Active User
  - platform: mqtt
    state_topic: 'ha/pc/display'
    name: N2 Active display
  - platform: mqtt
    state_topic: 'ha/pc/odroid/timeRemaining'
    name: N2 Odroid time remaining
    value_template: '{{ value | int }}'
    unit_of_measurement: 'minutes'
  - platform: mqtt
    state_topic: 'ha/pc/application'
    name: N2 Active application

binary_sensor:
  - platform: mqtt
    state_topic: 'ha/pc/screensaver'
    name: N2 Screensaver
    payload_on: True
    payload_off: False
```

Once you reload Home Assistant's configuration you can add the new items in the Lovelace web interface. Below is a sample configuration based on the values above.

Add an entities panel with this configuration:
```
entities:
  - entity: sensor.n2_active_user
  - entity: sensor.n2_active_display
  - entity: sensor.n2_active_application
  - entity: binary_sensor.n2_screensaver
  - entity: input_number.pc_odroid_time_remaining
  - entity: sensor.n2_odroid_time_remaining
  - entity: switch.n2_pc_enable_screenshot
show_header_toggle: false
title: N2
type: entities
```
Add a picture-entity panel with this config:
```
camera-view: live
entity: camera.n2_pc_display
type: picture-entity
```

The end result should look like this:
![Home Assistant integration](https://imgur.com/69WVzRt.png)


You will also need to set up some automations to be able to change the time allowance for a user. Make your edits in automations.yaml and restart Home Assistant:
```
- id: '1557839383'
  alias: N2 change remaining time for Odroid
  trigger:
  - entity_id: input_number.pc_odroid_time_remaining
    platform: state
  action:
  - data:
      payload: '{{ states(input_number.pc_odroid_time_remaining) | int }}'
      retain: true
      topic: ha/pc/odroid/timeRemaining
    service: mqtt.publish

- id: '1562675409185'
  alias: N2 get remaining time for Odroid
  trigger:
  - platform: mqtt
    topic: ha/pc/odroid/timeRemaining
  condition: []
  action:
  - data_template:
      entity_id: input_number.pc_odroid_time_remaining
      value: '{{ trigger.payload }}'
    service: input_number.set_value

- id: '1562675848675'
  alias: N2 set daily time allowance for user Odroid
  trigger:
  - at: 00:15:00
    platform: time
  condition: []
  action:
  - data:
      payload: 35
      retain: true
      topic: ha/pc/odroid/timeRemaining
    service: mqtt.publish
```
The last automation sets the daily allowed time for the odroid user to 35 minutes and runs at 00:15. This is just an example. You can devise your own automations which define when the user can use the computer. For example, if you want to give access only during a time interval you could run an automation to add allowance at the desired start time and a different automation to remove allowance before bed-time. You can control the amount of time each user is allowed based on things like school-day (https://www.home-assistant.io/components/workday/) or maybe if they've finished their chores (I'd like to hear how you can measure that automatically).

# Bugs and future improvements
None of the code I write is perfect, and this is no exception. There are some problems and ways around mqttNanny that I've identified so far (patches/ideas welcome). The program is intended to lock out a person with little Linux experience, so it won't be very effective against a seasoned sysadmin.
* When running in local mode there is no built-in mechanism to give more time to the user. If the computer is on for an extended period of time you need to restart the mqttNanny service daily to add a daily allowance. So it might not work as expected if you suspend your computer instead of shutting it down.
* When switching between local/remote modes data received from the MQTT broker has higher priority. For example the kid could start with no network connectivity, use up their default allowance and then restart with network connectivity to the broker. They would receive their remote allowance as if nothing happened. 
* When running in local mode the protection is weak if the user can change the system time. They could "borrow" time from other days in the future/past.
* Only the X11 session is monitored/locked. The user can log in a TTY before the lockdown, or via ssh with key authentication and can keep using the system (terminal based).
* If the user kills the screensaver process, there's nothing to lock the session. The process tries to lock the screensaver on 5 consecutive times and if it fails, it will shutdown the system instead. But the user could use the exploit in number 4 and unlock the screensaver from the command-line (could run a script to continuously unlock it).
* If the computer is not shut down gracefully (e.g. it's unplugged) you won't have the correct state in MQTT.
* The file /etc/mqttNanny.yaml used by the code needs to be readable only by root, since it holds your mqtt credentials. Otherwise the user could learn them and use mosquitto_pub to change their time allowance.
* The files that store used allowance per day located in /usr/local/share/mqttNanny/<username>/ aren't cleaned up automatically and may eventually fill up your disk in a few centuries (1.5MB/year). A cron job to delete old files may help.

I hope that future versions of the code will add support for other screensavers for linux, as well as MacOS and Windows support (the os-specific code is modular and should be easily extendable). Looking forward to issues/patches.
