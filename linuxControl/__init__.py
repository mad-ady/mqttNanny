import subprocess, os
import re
#sudo apt-get install python3-notify2
import notify2
import traceback
import time
#sudo apt-get install espeak
#sudo apt-get install xscreensaver
#sudo apt-get install xdotool
#sudo apt-get install imagemagick

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
              'stream': "ext://sys.stdout" }
    },
    root = {
        'handlers': ['c'],
        'level': logging.DEBUG,
    },
)

dictConfig(logging_config)
logger = logging.getLogger(__name__)

LOCAL_ALLOWANCE_PATH='/usr/local/share/mqttNanny/'

def externalNotify(program, message):
    """Send a message out via telegram or external script"""
    subprocess.run([program, message], stdout=subprocess.PIPE, universal_newlines=True)

def getCurrentDisplay():
    """Find the active TTY of this system"""
    result = subprocess.run(['fgconsole'], stdout=subprocess.PIPE, universal_newlines=True)
    return result.stdout.rstrip()

def getUserForDisplay(tty):
    """Find which user is logged in that TTY"""
    result = subprocess.run(['w'], stdout=subprocess.PIPE, universal_newlines=True)
    user = None
    display = None
    for line in iter(result.stdout.splitlines()):
        match = re.match(r'^([^\s]+)\s+tty{}\s+(:[0-9]+)\s+'.format(tty), line)
        if match:
            user = match.group(1)
            display = match.group(2)
    if user:
        return (user, display)
    else:
        raise Exception("Unable to find any user logged on tty{}".format(tty))

def disableUser(username):
    """Disable a system account"""
    subprocess.run(['passwd', '--lock', username], stdout=subprocess.PIPE, universal_newlines=True)

def enableUser(username):
    """Enable a system account"""
    subprocess.run(['passwd', '--unlock', username], stdout=subprocess.PIPE, universal_newlines=True)

def giveRootAccessToDisplay(user, display):
    """Allow root user to query/run programs on other user's displays"""
    subprocess.run('sudo -u {} DISPLAY={} xhost si:localuser:root'.format(user, display), shell=True, universal_newlines=True, check=False)

def hasRootAccessToDisplay(display):
    """Check if the user can run programs on the user's display"""
    os.environ['DISPLAY'] = display
    result = subprocess.run('xdotool get_desktop', stdout=subprocess.PIPE, shell=True, check=False)
    if result.returncode:
        return False
    else:
        return True

def lockScreensaver(display):
    """Turn on the screensaver"""
    os.environ['DISPLAY'] = display
    return subprocess.run('xscreensaver-command -lock', shell=True, universal_newlines=True, check=False).returncode

def shutdown():
    """Turn off the computer"""
    return subprocess.run('poweroff', shell=True, universal_newlines=True, check=False).returncode

def getActiveWindowName(display):
    """Get the name/titlebar of the active window"""
    os.environ['DISPLAY'] = display
    result = subprocess.run('xdotool getwindowfocus getwindowname', shell=True, universal_newlines=True, check=False, stdout=subprocess.PIPE)
    return result.stdout.rstrip()

def notify(text, currentDisplay):
    """Show a notification"""
    os.environ['DISPLAY'] = currentDisplay
    msg = text

    try:
        notify2.init("Nanny")
        n = notify2.Notification(msg, msg, "notification-power-disconnected" )
        n.set_timeout(5000)
        n.show()
    except Exception as e:
        logger.warning(e)
        logger.warning(traceback.format_exc())

def notifyTime(remainingTime, currentDisplay):
    """Show a notification and audio of remaining time"""
    os.environ['DISPLAY'] = currentDisplay
    msg = None
    if remainingTime > 0:
        msg = "{} minutes left".format(str(remainingTime))
    else:
        msg = "Time's up!"

    try:
        notify2.init("Nanny")
        n = notify2.Notification(msg, msg, "notification-power-disconnected" )
        n.set_timeout(5000)
        n.show()
        #have it speak via espeak
        subprocess.run('echo "'+ msg +'" | espeak', shell=True, check=False, timeout=5)
    except Exception as e:
        logger.warning(e)
        logger.warning(traceback.format_exc())

def isScreensaverOn(display):
    """Is the screensaver active?"""
    os.environ['DISPLAY'] = display
    result = subprocess.run('xscreensaver-command -time', shell=True, universal_newlines=True, check=False, stdout=subprocess.PIPE)

    for line in iter(result.stdout.splitlines()):
        logger.debug(line)
        match = re.search(r'screen (blanked|locked) since', line)
        if match:
            return True
        else:
            return False

def getScreenshot(display, yres=0):
    """Grab a screenshot of the active display and convert it to jpeg.
        Returns the binary jpeg data as bytes."""
    resize = ''
    if yres != 0:
        #specific resolution
        resize = '-resize x{}'.format(str(yres))
    command = 'xwd -root -display {}  | convert xwd:- {} jpg:- '.format(display, resize)
    logger.debug(command)
    result = subprocess.run(command, shell=True, check=False, stdout=subprocess.PIPE)
    return result.stdout

def makeLocalAllowanceFile(user, value, force=False):
    """Create a local file where to store the default/remaining allowance for the specific user for today"""
    if not os.path.exists(LOCAL_ALLOWANCE_PATH+user):
        logger.debug("Creating {}".format(LOCAL_ALLOWANCE_PATH+user))
        os.makedirs(LOCAL_ALLOWANCE_PATH+user,0o600, True)
    today = time.strftime("%Y-%m-%d")
    filename = LOCAL_ALLOWANCE_PATH+user+"/"+today
    if not os.path.exists(filename) or force:
        logger.debug("Writing {} to  {}".format(str(value), filename))
        f= open(filename,"w+")
        f.write(str(value))
        f.close()

def getLocalAllowance(user):
    """Read back the user's current allowance"""
    toReturn=0
    today = time.strftime("%Y-%m-%d")
    filename = LOCAL_ALLOWANCE_PATH + user + "/" + today
    try:
        f= open(filename,"r")
        value = f.readline()
        toReturn = int(value)
    except:
        logger.warning("Unable to read from local allowance file. Returning 0...")
    return toReturn

def setLocalAllowance(user, value):
    """Force write the allowance to file (periodic updates)"""
    makeLocalAllowanceFile(user, value, True)

if __name__ == '__main__':
    """Do a bit of unit testing"""
    currentTTY = getCurrentDisplay()
    print("Current display is {}\n".format(currentTTY))
    try:
        (currentUser, currentDisplay) = getUserForDisplay(currentTTY)
        print("Current user is {}\n".format(currentUser))
        print("Current application name is {}\n".format(getActiveWindowName(currentDisplay)))
        print("lockScreensaver({})...\n".format(currentDisplay))
        lockScreensaver(currentDisplay)
        time.sleep(5)
        print("isScreensaverOn({})? {}\n".format(currentDisplay, isScreensaverOn(currentDisplay)))
        notify(5, currentDisplay)
        notify(0, currentDisplay)
        time.sleep(2)
        print("Grabbing a screenshot and saving it as screenshot.jpg...")
        jpg = getScreenshot(currentDisplay, 720)
        with open('screenshot.jpg', 'wb') as file:
            file.write(jpg)

    except Exception as e:
        print(e)
    disableUser('teo')
    enableUser('teo')


