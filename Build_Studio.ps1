param([switch]$CreateInstaller, [string]$ISCC = '')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (!(Test-Path '.venv\Scripts\python.exe')) {
    py -3 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Cannot create Python environment' }
}
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& '.\.venv\Scripts\python.exe' -m PyInstaller --noconfirm --clean --windowed --onedir --name ExeBuilderStudio --icon assets/app.ico --add-data 'assets:assets' --add-data 'Ensure-Certificate.ps1:.' --add-data 'SigningOperations.ps1:.' main.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
Copy-Item -LiteralPath '.\Ensure-Certificate.ps1' -Destination '.\dist\ExeBuilderStudio\Ensure-Certificate.ps1' -Force
Write-Host 'Ready: dist\ExeBuilderStudio\ExeBuilderStudio.exe'
if ($CreateInstaller) {
    if (-not $ISCC) {
        $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
        if ($command) { $ISCC = $command.Source }
        foreach ($root in @(${env:ProgramFiles(x86)}, $env:ProgramFiles)) {
            foreach ($edition in @('Inno Setup 7','Inno Setup 6')) {
                $candidate = Join-Path $root ($edition + '\ISCC.exe')
                if (-not $ISCC -and (Test-Path -LiteralPath $candidate)) { $ISCC = $candidate }
            }
        }
    }
    if (-not $ISCC -or -not (Test-Path -LiteralPath $ISCC)) { throw 'Install Inno Setup or provide -ISCC <path to ISCC.exe>.' }
    & $ISCC '.\installer\ExeBuilderStudio.iss'
    if ($LASTEXITCODE -ne 0) { throw 'Inno Setup build failed' }
    Write-Host 'Ready: installer_output\ExeBuilderStudio_Setup.exe'
}
