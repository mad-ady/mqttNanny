# This PS1 script is called periodically via a scheduled task
# through a vbs loader, so that you don't get a PS1 shell briefly
# appearing on your screen. 
# Its purpose is to enhance the data reported back to mqttNanny service
# because the service can't access some of the data without running in the
# user context.
# The script does the following
# - if there is a mqttNanny-wantScreenshot.txt file in %TEMP%, it snaps a screenshot
#   and deletes this flag. mqttNanny will handle reading the screenshot
# - dumps the active window name to %TEMP%/mqttNanny-activeWindow.txt
# - reads from mqttNanny-notify.txt and generates a notification (and deletes this file)
# For notifications to display, you need to set Focus assist in windows settings:
# https://www.askvg.com/windows-10-fix-notifications-not-showing-while-playing-games-or-full-screen-videos/
[CmdletBinding()]            
Param(            
)            
Add-Type @"
  using System;
  using System.Runtime.InteropServices;
  public class UserWindows {
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
}
"@  

# Handle the screenshot functionality
$screenshotFlag = "$env:TEMP/mqttNanny-wantScreenshot.txt"
if (Test-Path -Path $screenshotFlag -PathType Leaf){
    [Reflection.Assembly]::LoadWithPartialName("System.Drawing")
    function screenshot([Drawing.Rectangle]$bounds, $path) {
        $bmp = New-Object Drawing.Bitmap $bounds.width, $bounds.height
        $graphics = [Drawing.Graphics]::FromImage($bmp)

        $graphics.CopyFromScreen($bounds.Location, [Drawing.Point]::Empty, $bounds.size)

        $bmp.Save($path)

        $graphics.Dispose()
        $bmp.Dispose()
    }
    #screen bounds
    $width = Get-WmiObject -Class Win32_DesktopMonitor | Select-Object -expand ScreenWidth
    $height = Get-WmiObject -Class Win32_DesktopMonitor | Select-Object -expand ScreenHeight
    $bounds = [Drawing.Rectangle]::FromLTRB(0, 0, $width, $height)
    $filename = "$env:TEMP/mqttNanny-screenshot.jpg"
    #snap the screnshot
    screenshot $bounds $filename
    #delete the flag
    Remove-Item $screenshotFlag
}

# Handle active window name
          
try {
    $filename = "$env:TEMP/mqttNanny-activeWindow.txt"            
    $ActiveHandle = [UserWindows]::GetForegroundWindow()            
    $Process = Get-Process | ? {$_.MainWindowHandle -eq $activeHandle}            
    $processName = $Process | Select ProcessName, @{Name="AppTitle";Expression= {($_.MainWindowTitle)}}            
    echo $processName
    # write to a file
    $processName | Out-File $filename
} catch {            
     Write-Error "Failed to get active Window details. More Info: $_"            
}

# Handle notifications
$notification = "$env:TEMP/mqttNanny-notify.txt"
if (Test-Path -Path $notification -PathType Leaf){
    $title = ""
    $message = ""
    $count = 0
    # notification has two lines - first is the title, second is the message
    foreach($line in Get-Content $notification) {
        if( $count -eq 0){
            $title = $line
        }
        if( $count -eq 1){
            $message = $line
        }
        $count++
    }
    Add-Type -AssemblyName System.Windows.Forms
    $global:balmsg = New-Object System.Windows.Forms.NotifyIcon
    $path = (Get-Process -id $pid).Path
    $balmsg.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon($path)
    $balmsg.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Warning
    $balmsg.BalloonTipText = "$message"
    $balmsg.BalloonTipTitle = $title
    $balmsg.Visible = $true
    $balmsg.ShowBalloonTip(5000)
    #delete the file
    Remove-Item $notification
}