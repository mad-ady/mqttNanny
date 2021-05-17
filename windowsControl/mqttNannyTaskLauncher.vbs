'We need to launch a vbs via scheduled task, so that the powershell console does not flash on screen every minute...
'See: 
'https://github.com/PowerShell/PowerShell/issues/3028

Dim shell, command
'Sadly it's difficult to escape spaces or use variables..
'So we convert c:\Program Files to C:\Progra~1
command = "powershell.exe -nologo -File c:\Progra~1\mqttNanny\windowsControl\mqttNanny.ps1"
Set shell = CreateObject("WScript.Shell")
Shell.Run command,0