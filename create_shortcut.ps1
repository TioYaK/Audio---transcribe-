$ScriptDir = $PSScriptRoot
$PythonScriptPath = Join-Path -Path $ScriptDir -ChildPath "monitor_transcricoes.py"
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path -Path $DesktopPath -ChildPath "Mirror AI Monitor.lnk"

try {
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    
    # Check for pythonw (no console) or python
    if (Get-Command "pythonw" -ErrorAction SilentlyContinue) {
        $Shortcut.TargetPath = "pythonw"
    }
    else {
        $Shortcut.TargetPath = "python"
    }
    
    $Shortcut.Arguments = """$PythonScriptPath"""
    $Shortcut.WorkingDirectory = $ScriptDir
    $Shortcut.Description = "Monitor de Transcrições Mirror.ia"
    $Shortcut.Save()
    
    Write-Host "Atalho criado com sucesso na Área de Trabalho: $ShortcutPath"
}
catch {
    Write-Error "Erro ao criar atalho: $_"
    exit 1
}
