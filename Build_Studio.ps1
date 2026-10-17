param([switch]$CreateInstaller, [string]$ISCC = '', [ValidateSet('Standard','Offline')][string]$Mode = 'Standard')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (!(Test-Path '.venv\Scripts\python.exe')) {
    py -3 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Cannot create Python environment' }
}
if ($Mode -eq 'Offline') {
    $wheelhouse = Join-Path $PSScriptRoot 'offline_tools\windows\wheelhouse'
    if (!(Test-Path -LiteralPath $wheelhouse)) { throw "Offline mode requires $wheelhouse with all build wheels. See offline_tools/README.md." }
    & '.\.venv\Scripts\python.exe' -m pip install --no-index --find-links $wheelhouse -r requirements.txt
} else {
    & '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
}
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
if ($Mode -eq 'Offline') {
    $wheelhouse = Join-Path $PSScriptRoot 'offline_tools\windows\wheelhouse'
    & '.\.venv\Scripts\python.exe' -m pip install --no-index --find-links $wheelhouse 'pyinstaller>=6.10,<7'
} else {
    & '.\.venv\Scripts\python.exe' -m pip install 'pyinstaller>=6.10,<7'
}
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller dependency installation failed' }
# Remove any previously staged tool payload so Standard builds cannot accidentally include stale Offline tools.
$distTools = Join-Path $PSScriptRoot 'dist\ExeBuilderStudio\tools'
if (Test-Path -LiteralPath $distTools) { Remove-Item -LiteralPath $distTools -Recurse -Force }

& '.\.venv\Scripts\python.exe' -m PyInstaller --noconfirm --clean --windowed --onedir --name ExeBuilderStudio --icon assets/app.ico --add-data 'assets:assets' main.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
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
    if ($Mode -eq 'Offline') {
        $required = @('jdk\bin\jpackage.exe','python\python.exe','inno\ISCC.exe')
        foreach ($rel in $required) { if (!(Test-Path -LiteralPath (Join-Path $PSScriptRoot ('offline_tools\windows\' + $rel)))) { throw "Offline mode is missing offline_tools\windows\$rel. See offline_tools/README.md." } }
        $offlineRoot = Join-Path $PSScriptRoot 'offline_tools\windows'
        $toolRoot = Join-Path $PSScriptRoot 'dist\ExeBuilderStudio\tools'
        New-Item -ItemType Directory -Path $toolRoot -Force | Out-Null
        foreach ($tool in @('jdk','python','inno')) {
            $source = Join-Path $offlineRoot $tool
            $target = Join-Path $toolRoot $tool
            Copy-Item -LiteralPath $source -Destination $target -Recurse -Force
        }
        $wheelhouse = Join-Path $offlineRoot 'wheelhouse'
        if (!(Test-Path -LiteralPath $wheelhouse)) { throw "Offline mode requires $wheelhouse. See offline_tools/README.md." }
        & $ISCC '/DInstallerMode="Offline"' '.\installer\ExeBuilderStudio.iss'
    } else { & $ISCC '/DInstallerMode="Standard"' '.\installer\ExeBuilderStudio.iss' }
    if ($LASTEXITCODE -ne 0) { throw 'Inno Setup build failed' }
    Write-Host ("Ready: installer_output\ExeBuilderStudio_{0}_Setup.exe" -f $Mode)
}
