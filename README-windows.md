== Windows dependencies/limitations ==
 - Requires Windows 10 Pro (the Home version lacks some of the tools needed, like query user), at least version 2004
 - Requires PowerShell at least version 5.1
```
PS C:\WINDOWS\system32> $psversiontable.psversion

Major  Minor  Build  Revision
-----  -----  -----  --------
5      1      18362  1171
PS C:\WINDOWS\system32> query user
 USERNAME              SESSIONNAME        ID  STATE   IDLE TIME  LOGON TIME
>user1                 console             1  Active          .  2/4/2021 11:26 AM
 user2                                     4  Disc            4  2/4/2021 12:21 PM
 user3                                     5  Disc            .  2/4/2021 12:24 PM
```

 - Requires (should come with windows): 
    - %WINDIR%\system32\query.exe
    - %WINDIR%\system32\tsdiscon.exe

 - Users need to be local (not microsoft accounts)
 - Username can have spaces, but needs to be shorter than 22 characters (apparently local windows accounts are limited to 20)
 - Requires you to enable executing privileged unsigned PowerShell scripts (as Administrator! - warning!):  https:/go.microsoft.com/fwlink/?LinkID=135170. These are needed to run the ps1 scripts to grab window name, display notification and take screenshot.
   Run this in a PowerShell ran as Administrator
```
 Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope LocalMachine
```
 - In order to get notifications pop up even when playing games/full screen content, you need to explicitly enable them in Windows Settings:
  https://www.askvg.com/windows-10-fix-notifications-not-showing-while-playing-games-or-full-screen-videos/
  WIN + I -> Focus Assist -> Automatic Rules -> Disable "While playing a game/When I'm using an app in full screen mode"

== Installation ==
Install python3 (e.g. via `choco install python3 pip`)

From an Administrator PowerShell run:
```
pip install paho-mqtt pyYaml wmi
```

== Task Scheduler ==
Individual users can run a periodic task via Task Scheduler to: 
 - export current application name
 - snap screenshot on demand
 - receive notifications

Start Task Scheduler (as each user) -> Create Task -> 
 General:
 - Name: mqttNanny
 - Run only when user is logged on
 Triggers:
 - New -> Begin a task At logon
 - Specific User
 - Repeat task every 1 minute for a duration of Indefinitely
 - Enabled
 Actions:
 - New -> Start a program
 - Program/script -> Browse -> C:\Program Files\mqttNanny\windowsControl\mqttNannyTaskLauncher.vbs

Next, log out and back in to the account, to start the task.


== Caveats ==
Because of how `query user` command reports active users you have the following situation. When the computer is in the logon screen (that displays a fullscreen image) and the user list is not visible, then the system thinks the screensaver is on and doesn't tick down time. If instead, you are at the logon screen, ready to enter a password (for any user), even if you haven't entered the password, the system will report the currently selected user as active (and screensaver will be marked as off). Thankfully windows will revert to the picture logon screen after ~30s of inactivity, so it shouldn't waste too much time...