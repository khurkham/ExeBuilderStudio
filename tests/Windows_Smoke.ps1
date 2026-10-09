param([string]$SignTool = '', [string]$SampleExe = '')
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
# Parse scripts before changing any Windows certificate store.
foreach ($file in @('Ensure-Certificate.ps1','SigningOperations.ps1','Build_Studio.ps1')) {
    $tokens = $null; $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $project $file), [ref]$tokens, [ref]$parseErrors) | Out-Null
    if ($parseErrors) { throw ($parseErrors | Out-String) }
}
if (-not $SignTool) {
    $SignTool = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
}
if (-not $SignTool -or -not (Test-Path -LiteralPath $SignTool)) { throw 'Provide -SignTool <signtool.exe path>.' }
if (-not $SampleExe) { $SampleExe = Join-Path $env:SystemRoot 'System32\where.exe' }
if (-not (Test-Path -LiteralPath $SampleExe)) { throw 'Provide -SampleExe <test executable>.' }
$directory = Join-Path $env:LOCALAPPDATA 'ExeBuilderStudio\certificates'
$metadata = Join-Path $directory 'certificate.json'
$previous = if (Test-Path -LiteralPath $metadata) { [System.IO.File]::ReadAllBytes($metadata) } else { $null }
$publisher = 'EBS Smoke ' + [guid]::NewGuid().ToString('N')
$testDirectory = Join-Path $env:TEMP $publisher
New-Item -ItemType Directory -Path $testDirectory | Out-Null
$certificate = $null
try {
    $raw = & (Join-Path $project 'Ensure-Certificate.ps1') -Publisher $publisher
    if ($LASTEXITCODE -ne 0) { throw 'Certificate creation failed.' }
    $first = ($raw | Where-Object { $_ -like 'EBS_JSON:*' } | Select-Object -Last 1).Substring(9) | ConvertFrom-Json
    $certificate = Get-Item ('Cert:\CurrentUser\My\' + $first.thumbprint)
    if (-not $certificate.HasPrivateKey -or -not $first.created) { throw 'Test certificate is missing its private key.' }
    $raw = & (Join-Path $project 'Ensure-Certificate.ps1') -Publisher $publisher
    if ($LASTEXITCODE -ne 0) { throw 'Certificate reuse failed.' }
    $second = ($raw | Where-Object { $_ -like 'EBS_JSON:*' } | Select-Object -Last 1).Substring(9) | ConvertFrom-Json
    if ($second.created -or $second.thumbprint -ne $first.thumbprint) { throw 'Certificate should be reused.' }
    $copy = Join-Path $testDirectory 'Sample.exe'
    Copy-Item -LiteralPath $SampleExe -Destination $copy
    & $SignTool sign /fd SHA256 /s My /sha1 $first.thumbprint $copy
    if ($LASTEXITCODE -ne 0) { throw 'SignTool test signing failed.' }
    $signature = Get-AuthenticodeSignature -LiteralPath $copy
    if (-not $signature.SignerCertificate -or $signature.SignerCertificate.Thumbprint -ne $first.thumbprint) { throw 'Expected embedded test signature not found.' }
    if ($signature.Status -in @('HashMismatch','NotSigned')) { throw 'Signature integrity check failed.' }
    Write-Host ('PASS: certificate creation, reuse and EXE signing. Windows trust status: ' + $signature.Status)
    Write-Host 'A self-signed TEST certificate is not automatically trusted; no trusted root was installed.'
} finally {
    if ($certificate) {
        Remove-Item ('Cert:\CurrentUser\My\' + $certificate.Thumbprint) -DeleteKey -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath (Join-Path $directory ($certificate.Thumbprint + '.cer')) -ErrorAction SilentlyContinue
    }
    if ($null -ne $previous) { [System.IO.File]::WriteAllBytes($metadata,$previous) }
    else { Remove-Item -LiteralPath $metadata -ErrorAction SilentlyContinue }
    Remove-Item -LiteralPath $testDirectory -Recurse -Force
}
