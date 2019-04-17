import linuxControl
import paho.mqtt.client as mqtt
import yaml
import os

# Prerequisites:
# * pip: sudo apt-get install python-pip
# * paho-mqtt: pip install paho-mqtt
# * python-yaml: sudo apt-get install python-yaml
# * notify2: sudo apt-get install python3-notify2
#sudo apt-get install espeak
#sudo apt-get install xscreensaver
#sudo apt-get install xdotool
#sudo apt-get install imagemagick

# Configuration file goes in /etc/mqttNanny.yaml and should contain something like:
# TODO

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
            print(exc)
            print("Unable to parse configuration file /etc/mqttNanny.yaml")
            sys.exit(1)

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    (result, mid) = client.subscribe(conf['command_topic'])
    print("Got subscription result for " + conf['command_topic'] + ":" + str(result))

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print("Received command:" + msg.topic + " " + str(msg.payload))

    # listen to requests, process them
    # set the replies over mqtt
    if msg.topic == conf['test']:
        if msg.payload == 'test':
            pass

""" Initialize the MQTT object and connect to the server """
parseConfig()
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
if conf['mqttUser'] and conf['mqttPass']:
    client.username_pw_set(username=conf['mqttUser'], password=conf['mqttPass'])
client.connect(conf['mqttServer'], conf['mqttPort'], 60)
#listen for messages and call on_message when needed
print("Listen to MQTT messages...")
sys.stdout.flush()
client.loop_forever()