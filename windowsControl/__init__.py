import subprocess, os
import re
import traceback
import time
import logging
from logging.config import dictConfig

localPath = os.path.dirname(os.path.realpath(__file__))


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
              'filename': localPath+"\\windowsControl.log",
              'maxBytes': 1000000,
              'backupCount': 4
        }
    },
    
    root = {
        'handlers': ['c', 'f'],
        'level': logging.DEBUG,
    },
)

dictConfig(logging_config)
logger = logging.getLogger(__name__)


LOCAL_ALLOWANCE_PATH=localPath

def externalNotify(program, message):
    """Send a message out via telegram or external script"""
    subprocess.run([program, message], stdout=subprocess.PIPE, universal_newlines=True)

def getCurrentDisplay():
    """Find the active TTY of this system"""
    # Windows reports the active display as 'console', so we hardcode it
    return "console"

def getUserForDisplay(tty):
    """Find which user is logged in that TTY"""

    #We'll use "query user" windows powershell command (requires Windows Pro!)
    #PS C:\Users\user1> query user
    #USERNAME              SESSIONNAME        ID  STATE   IDLE TIME  LOGON TIME
    #>user1                 console             1  Active         10  2/4/2021 11:26 AM
    # user2                                     4  Disc           14  2/4/2021 12:21 PM
    # user3                                     5  Disc           10  2/4/2021 12:24 PM
    
    result = subprocess.run(['powershell.exe', "-Command", "query user"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    logger.info("Running command {}".format(result.args))
    for line in iter(result.stderr.splitlines()):
        logger.warning(line)

    user = None
    display = None
    for line in iter(result.stdout.splitlines()):
        logger.debug(line)
        #we're only looking for the active tty (e.g. console)
        match = re.match(r'^(\s|\>)(......................)('+tty+')\s+', line)
        if match:
            logger.debug("Matched line "+line)
            current_session = match.group(1)
            user = match.group(2).rstrip(" ")
            display = match.group(3)
    if user:
        return (user, display)
    else:
        raise Exception("Unable to find any user logged on {}".format(tty))
    

def disableUser(username):
    """Disable a system account"""
    result = subprocess.run(['powershell.exe', '-Command', 'Disable-LocalUser', '-name', '"'+username+'"'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    logger.info("Running command {}".format(result.args))
    for line in iter(result.stdout.splitlines()):
        logger.debug(line)
    for line in iter(result.stderr.splitlines()):
        logger.warning(line)

def enableUser(username):
    """Enable a system account"""
    result = subprocess.run(['powershell.exe', '-Command', 'Enable-LocalUser', '-name', '"'+username+'"'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    logger.info("Running command {}".format(result.args))
    for line in iter(result.stdout.splitlines()):
        logger.debug(line)
    for line in iter(result.stderr.splitlines()):
        logger.warning(line)

def giveRootAccessToDisplay(user, display):
    """Allow root user to query/run programs on other user's displays"""
    # not necessary on windows
    pass

def hasRootAccessToDisplay(display):
    """Check if the user can run programs on the user's display"""
    # not necessary on windows
    return True

def lockScreensaver(display, screensaver="xscreensaver"):
    """For windows, we send the user to the login screen"""
    result = subprocess.run(['tsdiscon.exe', 'console'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=False)
    logger.info("Running command {}".format(result.args))
    for line in iter(result.stdout.splitlines()):
        logger.debug(line)
    for line in iter(result.stderr.splitlines()):
        logger.warning(line)
    # hopefully the user was disconnected.
    return 0

def shutdown():
    """Turn off the computer"""
    return subprocess.run(["powershell.exe", "-Command", "Stop-Computer", "-ComputerName", "localhost"], shell=True, universal_newlines=True, check=False).returncode

def getActiveWindowName(display):
    """Get the name/titlebar of the active window"""
    # first, get the active user on the display
    (user, display) = getUserForDisplay(display)
    
    # calls the external activeWindowName.ps1 script to do the dirty work
    result = subprocess.run(['powershell.exe', "-Command", localPath+"\\activeWindowName.ps1"], shell=True, universal_newlines=True, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logger.info("Running command {}".format(result.args))
    #powershell.exe -Command .\activeWindowName.ps1
    #
    #ProcessName     UserName                AppTitle
    #-----------     --------                --------
    #WindowsTerminal DESKTOP-KHG5C3F\user1   Administrator: Windows PowerShell    
    
    
    processNameLength = 0
    userNameLength = 0
    dashesMatched = False
    activeWindows = []

    for line in iter(result.stdout.splitlines()):
        #ignore blank lines
        if re.match('^\s*$', line):
            continue
        logger.debug(line)
        # look for -----------     --------                --------
        matchDashes = re.match(r'^([-]+\s+)([-]+\s+)([-]+\s*)', line)
        if matchDashes:
            # we need to count the length of the columns so that we can more easily parse it
            processNameLength = len(matchDashes.group(1))
            userNameLength = len(matchDashes.group(2))
            logger.debug("processNameLength = {}, userNameLength = {}".format(processNameLength, userNameLength))
            dashesMatched = True
            continue
        
        if dashesMatched:
            # we'll split the line based on length
            # some lines may not have all the data, skip them
            if len(line) >= processNameLength + userNameLength:
                processName = line[0:processNameLength].rstrip(" ")
                userName = line[processNameLength:processNameLength+userNameLength].rstrip(" ")
                title = line[processNameLength+userNameLength:].rstrip(" ") #till the string end

                # from the user cut out the domain (computer name)
                try:
                    userName = userName.split("\\")[1]
                    # transform the username to lowercase
                    userName = userName.lower()
                    logger.debug("Extracted processName: {}, username: {}, title: {}".format(processName, userName, title))

                    # make sure the active window belongs to the active user (may be redundant? I don't know)
                    if userName == user:
                        activeWindows.append(processName + ": " + title)
                except:
                    logger.warning("Unable to extract username")
            
        
    for line in iter(result.stderr.splitlines()):
        logger.warning(line)
    
    if len(activeWindows) == 1:
        #this is normal, one active window
        return activeWindows[0]
    elif len(activeWindows) == 0:
        return "No window"
    else:
        # more than one active window is a problem - couldn't get active windows...
        logger.warning("Found "+str(len(activeWindows))+" active windows. This is not ok.")
        return "Error - couldn't get active window"

def notify(text, currentDisplay):
    """Show a notification"""
    msg = text
    user = ""
    try:
        (user, display) = getUserForDisplay(currentDisplay)
    except:
        pass
    result = subprocess.run(['powershell.exe', "-file", localPath+"\\notification.ps1", "Attention, "+user, msg], shell=True, universal_newlines=True, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logger.info("Running command {}".format(result.args))
    for line in iter(result.stdout.splitlines()):
        logger.debug(line)
    for line in iter(result.stderr.splitlines()):
        logger.warning(line)

def notifyTime(remainingTime, currentDisplay):
    """Show a notification of remaining time"""
    msg = None
    if remainingTime > 0:
        msg = "{} minutes left".format(str(remainingTime))
    else:
       msg = "Time's up!"
    
    notify(msg, currentDisplay)

def isScreensaverOn(display, screensaver="xscreensaver"):
    """For windows - is the login screen active?"""
    # note that because of windows - only if the lockscreen shows no users is it considered as "on"
    # if you are in the user selection section, the selected user will be reported as active, even if you haven't logged in with that account!
    try:
        getUserForDisplay(getCurrentDisplay())
        logger.debug("We have a user logged on console.")
        return False
    except Exception as e:
        #no user logged on, we can consider that the screensaver is on
        logger.debug("Received exception "+str(e)+". Assuming lock screen is on...")
        return True
    
def getScreenshot(display, yres=0):
    """Grab a screenshot of the active display and convert it to jpeg.
        Returns the binary jpeg data as bytes."""
    screenshot = subprocess.run(["powershell.exe", "-Command", localPath+"\\screenshot.ps1", localPath+"\\screenshot.jpg"], shell=True, universal_newlines=True, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logger.debug("Running command {}".format(screenshot.args))
    for line in iter(screenshot.stdout.splitlines()):
        logger.debug(line)
    for line in iter(screenshot.stderr.splitlines()):
        logger.warning(line)

    # now, try to read the screenshot and return its bytes
    try:
        with open(localPath+"\\screenshot.jpg", 'rb') as file:
            return file.read()
    except Exception as e:
        logger.error("Error while reading screenshot: "+str(e))
        return ''


def makeLocalAllowanceFile(user, value, force=False):
    """Create a local file where to store the default/remaining allowance for the specific user for today"""
    if not os.path.exists(LOCAL_ALLOWANCE_PATH + "\\" + user):
        logger.debug("Creating {}".format(LOCAL_ALLOWANCE_PATH+user))
        os.makedirs(LOCAL_ALLOWANCE_PATH + "\\" +user,0o600, True)
    today = time.strftime("%Y-%m-%d")
    filename = LOCAL_ALLOWANCE_PATH + "\\" + user + "\\" + today
    if not os.path.exists(filename) or force:
        logger.debug("Writing {} to  {}".format(str(value), filename))
        f= open(filename,"w+")
        f.write(str(value))
        f.close()
    

def getLocalAllowance(user):
    """Read back the user's current allowance"""
    toReturn=0
    today = time.strftime("%Y-%m-%d")
    filename = LOCAL_ALLOWANCE_PATH + "\\" + user + "\\" + today
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
    print("Sleeping 15s...")
    time.sleep(25)
    currentTTY = getCurrentDisplay()
    print("Script directory is "+localPath)
    print("Current display is {}\n".format(currentTTY))
    try:
        (currentUser, currentDisplay) = getUserForDisplay(currentTTY)
        print("Current user is {}\n".format(currentUser))
        print("Current application name is {}\n".format(getActiveWindowName(currentDisplay)))
        #print("lockScreensaver({})...\n".format(currentDisplay))
        #lockScreensaver(currentDisplay)
        time.sleep(5)
        print("isScreensaverOn({})? {}\n".format(currentDisplay, isScreensaverOn(currentDisplay)))
        notifyTime(5, currentDisplay)
        notifyTime(0, currentDisplay)
        time.sleep(2)
        print("Grabbing a screenshot and saving it as screenshot.jpg...")
        jpg = getScreenshot(currentDisplay, 720)
        with open('../screenshot.jpg', 'wb') as file:
            file.write(jpg)

    except Exception as e:
        print(e)
    print("Disabling user...\n")
    disableUser('user de test')
    #enableUser('user de test')


