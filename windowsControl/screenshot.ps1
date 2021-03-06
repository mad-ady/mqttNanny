param ($filename)
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
$bounds = [Drawing.Rectangle]::FromLTRB(0, 0, 1920, 1080)

#$PC_name=$(Get-WmiObject Win32_Computersystem).name
#$dateandtime = Get-Date -Format yyyy-MM-dd-hh-mm-ss
#$path_pcname= "C:\" + $PC_name + "_screenshot_" + "$dateandtime"+ ".png"
#screenshot $bounds $path_pcname

screenshot $bounds $filename