'We need to launch a vbs via scheduled task, so that the powershell console does not flash on screen every minute...
'See: 
'https://github.com/PowerShell/PowerShell/issues/3028

Dim shell, command
command = "powershell.exe -nologo -File c:\Program Files\mqttNanny\mqttNanny.ps1"
Set shell = CreateObject("WScript.Shell")
Shell.Run command,0