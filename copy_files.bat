$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = "C:\Users\SaidJ\AppData\Roaming\MetaQuotes\Terminal\Common\Files"
$watcher.Filter = "*.*"
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true

Register-ObjectEvent $watcher "Created" -Action {
    param($source, $event)
    Copy-Item -Path $event.FullPath -Destination "C:\Users\SaidJ\OneDrive\Documentos\projects\forex_ml_bot\forex_ml_bot\live_trading_data" -Force
}

while ($true) { Start-Sleep 1 }