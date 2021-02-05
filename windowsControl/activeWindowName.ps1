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
try {            
$ActiveHandle = [UserWindows]::GetForegroundWindow()            
$Process = Get-Process -IncludeUserName | ? {$_.MainWindowHandle -eq $activeHandle}            
$Process | Select ProcessName, UserName, @{Name="AppTitle";Expression= {($_.MainWindowTitle)}}            
} catch {            
 Write-Error "Failed to get active Window details. More Info: $_"            
}