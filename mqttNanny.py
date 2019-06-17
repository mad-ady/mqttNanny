#!/usr/bin/python3
import linuxControl as computer
import paho.mqtt.client as mqtt
import yaml
import os
import threading
import time
import logging
from logging.config import dictConfig

logging_config = dict(
    version = 1,
    formatters = {
        'f': {'format':
              '%(asctime)s %(levelname)-8s [%(funcName)s:%(lineno)d] %(message)s'}
    },
    handlers = {
        'c': {'class': 'logging.StreamHandler',
              'formatter': 'f',
              'level': logging.DEBUG,
              'stream': "ext://sys.stdout" },
        'f': {
              'class': 'logging.handlers.RotatingFileHandler',
              'formatter': 'f',
              'filename': '/var/log/mqttNanny.log',
              'maxBytes': 1000000,
              'backupCount': 4
        }
    },
    root = {
        'handlers': ['c','f'],
        'level': logging.DEBUG,
    },
)

dictConfig(logging_config)
logger = logging.getLogger(__name__)


# Prerequisites:
# * pip: sudo apt-get install python3-pip
# * paho-mqtt: sudo pip3 install paho-mqtt
# * python-yaml: sudo apt-get install python3-yaml
# * notify2: sudo apt-get install python3-notify2
#sudo apt-get install espeak
#sudo apt-get install xscreensaver
#sudo apt-get install xdotool
#sudo apt-get install imagemagick

# On every account that you want to monitor you need to allow root to run X11 commands. On client login run:
# xhost si:localuser:root

# Configuration file goes in /etc/mqttNanny.yaml and should be similar to the example provided

# For startup copy mqttNanny.service to /etc/systemd/system/
# Startup is done via systemd with
#  sudo systemctl enable mqttNanny
#  sudo systemctl start mqttNanny

#Tips:
#/etc/mqttNanny.yaml should be readable only by root, in order not to expose your MQTT credentials to internal attackers

""" Parse and load the configuration file to get MQTT credentials """

conf = {}

def parseConfig():
    global conf
    with open("/etc/mqttNanny.yaml", 'r') as stream:
        try:
            conf = yaml.load(stream)
        except yaml.YAMLError as exc:
            logger.error(exc)
            logger.error("Unable to parse configuration file /etc/mqttNanny.yaml")
            sys.exit(1)

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    logger.info("Connected with result code " + str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    for user in conf['users']:
        topic = conf['baseTopic']+user+'/'+conf['mqttTimeTopicSuffix']
        (result, mid) = client.subscribe(topic)
        logger.info("Got subscription result for " + topic + ":" + str(result))

    #subscribe to the screenshotCommand topic
    (result, mid) = client.subscribe(conf['mqttScreenshotCommand'])
    logger.info("Got subscription result for " + conf['mqttScreenshotCommand'] + ":" + str(result))

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    logger.debug("Received command:" + msg.topic + " " + str(msg.payload))

    # listen to requests, process them
    # set the replies over mqtt
    timeTopics = {}
    for user in conf['users']:
        topic = conf['baseTopic']+user+'/'+conf['mqttTimeTopicSuffix']
        timeTopics[topic]=user
    	
    if msg.topic == conf['mqttScreenshotCommand']:
        if msg.payload == 'enable':
            # start a thread that will periodically post back screenshots for a set interval of time. At the end, it disables itself            
            pass
        if msg.payload == 'disable':
            # kill the screenshot thread if it exists
        	pass
    if msg.topic in timeTopics.keys():
        logger.debug("Processing {} for user {}".format(msg.topic, timeTopics[msg.topic]))
        #msg.payload should be the number of minutes left
        if t[timeTopics[msg.topic]] != int(msg.payload):
            oldTime = t[timeTopics[msg.topic]]
            logger.info("Set new time {} for user {}".format(int(msg.payload), timeTopics[msg.topic]))
            t[timeTopics[msg.topic]] = int(msg.payload)
            if t[timeTopics[msg.topic]] > 0 and oldTime <= 0:
                logger.info("Restoring user {}".format(timeTopics[msg.topic]))
                #might have been disabled, restore the user
                computer.enableUser(timeTopics[msg.topic])


""" Initialize the MQTT object and connect to the server """
parseConfig()
#Load default time for the monitored users
t={}
for user in conf['users']:
    t[user]=conf['users'][user]['defaultOfflineTime']
    logger.info("Loaded {} default minutes for {}".format(str(t[user]), user))
    # also, enable user (might have been disabled)
    computer.enableUser(user)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
if conf['mqttUser'] and conf['mqttPass']:
    client.username_pw_set(username=conf['mqttUser'], password=conf['mqttPass'])
try:
    client.connect(conf['mqttServer'], conf['mqttPort'], 60)
except:
    logger.warning("Unable to connect to MQTT Broker. Running with local limits")
    pass

oldTTY=None
oldDisplay=None
oldActiveUser=None
oldScreensaver=None
oldApplication=None

try:
    client.loop_start()
except:
    pass

"""	Main processing loop. Keep track of time for each user """

while True:
    """ Before starting give mqtt a chance to connect and get the remote data """
    time.sleep(int(conf['checkInterval']))

    #get active display
    tty=computer.getCurrentDisplay()
    if tty != oldTTY:
        #update the new value via mqtt
        oldTTY = tty
        if client:
            logger.debug("TTY change: {}".format(tty))
            client.publish(conf['baseTopic']+'tty', tty, 0, True)
    #get active user
    try:
        (activeUser, display) = computer.getUserForDisplay(tty)
        if activeUser != oldActiveUser:
            oldActiveUser = activeUser
            if client:
                logger.debug("User change: {}".format(activeUser))
                client.publish(conf['baseTopic']+'activeUser', activeUser, 0, True)
        if display != oldDisplay:
            oldDisplay = display
            if client:
                logger.debug("Display change: {}".format(display))
                client.publish(conf['baseTopic']+'display', display, 0, True)

        #check if root can run X11 applications and access the user's display
        if not computer.hasRootAccessToDisplay(display):
            logger.info("Allowing root access for display {}".format(display))
            computer.giveRootAccessToDisplay(activeUser, display)

        #is screensaver active?
        screensaver = computer.isScreensaverOn(display)
        if screensaver != oldScreensaver:
            oldScreensaver = screensaver
            if client:
                logger.debug("Screensaver change: {}".format(screensaver))
                client.publish(conf['baseTopic']+'screensaver', screensaver, 0, True)

        #current application name
        application = "Screensaver"
        if not screensaver:
            application = computer.getActiveWindowName(display)
        if application != oldApplication:
            oldApplication = application
            if client:
                logger.debug("Application change: {}".format(application))
                client.publish(conf['baseTopic']+'application', application, 0, True)
		
        # Check if the current user still has time allowed. Active screensaver does not consume time
        if not screensaver:
            t[activeUser] = int(t[activeUser] - conf['checkInterval']/60.0)
            logger.info("Tick down time for {}. Time left: {} min".format(activeUser, t[activeUser]))
            if t[activeUser] == 10:
                # 10 minutes left
                computer.notify(10, display)
            if t[activeUser] == 5:
                # 5 minutes left
                computer.notify(5, display)
            if t[activeUser] == 1:
                # final warning
                computer.notify(1, display)
            if t[activeUser] <= 0:
                computer.notify(0, display)
                time.sleep(4)
                # lock screensaver and disable user
                computer.disableUser(activeUser)
                computer.lockScreensaver(display)
            if client:
                client.publish(conf['baseTopic']+activeUser+'/'+conf['mqttTimeTopicSuffix'], t[activeUser], 0, True)

    except Exception as e:
        logger.warning(e)
        #invalidate the mqtt topics
        if client:
            client.publish(conf['baseTopic']+'activeUser', 'None', 0, True)
            client.publish(conf['baseTopic']+'display', 'None', 0, True)
            client.publish(conf['baseTopic']+'screensaver', False, 0, True)
            client.publish(conf['baseTopic']+'application', 'None', 0, True)
            oldActiveUser=None
            oldDisplay=None
            oldScreensaver=None
            oldApplication=None
