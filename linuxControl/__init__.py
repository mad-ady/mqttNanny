import subprocess, os
import re

def getCurrentDisplay():
    """Find the active TTY of this system"""
    result = subprocess.run(['fgconsole'], stdout=subprocess.PIPE)
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

def lockScreensaver(display):
    """Turn on the screensaver"""
    env = os.environ.copy()
    env['DISPLAY'] = display
    result = subprocess.run(['xscreensaver-command', '-lock'], env=env, shell=True, universal_newlines=True,
                            stdout=subprocess.PIPE)

def notify():
    """Show a notification and audio of remaining time"""
    pass

def isScreensaverOn(display):
    """Is the screensaver active?"""
    env = os.environ.copy()
    env['DISPLAY'] = display
    result = subprocess.run(['xscreensaver-command', '-time'], env=env, shell=True, universal_newlines=True, stdout=subprocess.PIPE)
    for line in iter(result.stdout.splitlines()):
        match = re.match(r'screen blanked since', line)
        if match:
            return True
        else:
            return False

if __name__ == '__main__':
    """Do a bit of unit testing"""
    currentTTY = getCurrentDisplay()
    print("Current display is {}\n".format(currentTTY))
    (currentUser, currentDisplay) = getUserForDisplay(currentTTY)
    print("Current user is {}\n".format(currentUser))
    disableUser('teo')
    enableUser('teo')
    print("lockScreensaver({})".format(currentDisplay))
    print("isScreensaverOn({})? {}\n".format(currentDisplay, isScreensaverOn(currentDisplay)))
