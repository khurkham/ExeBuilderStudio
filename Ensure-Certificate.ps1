param([string]$Publisher = '', [switch]$Quiet)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
try {
    $directory = Join-Path $env:LOCALAPPDATA 'ExeBuilderStudio\certificates'
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    $metadataPath = Join-Path $directory 'certificate.json'
    if (-not $Publisher -and (Test-Path -LiteralPath $metadataPath)) {
        try { $Publisher = (Get-Content -LiteralPath $metadataPath -Raw -Encoding UTF8 | ConvertFrom-Json).publisher } catch { }
    }
    if (-not $Publisher) { $Publisher = 'Khurkham' }
    # This value is data, never PowerShell source. Restrict X.500 separators.
    if ($Publisher.Length -gt 120 -or $Publisher -match '[,=+<>;"\\\r\n]' -or -not $Publisher.Trim()) {
        throw 'Use a publisher name without X.500 punctuation or line breaks.'
    }
    $subject = 'CN=' + $Publisher.Trim()
    $friendly = 'EXE Builder Studio - SELF-SIGNED TEST'
    $certificate = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
        Where-Object {
            $_.FriendlyName -eq $friendly -and $_.Subject -eq $subject -and $_.HasPrivateKey -and
            $_.NotBefore -le (Get-Date) -and $_.NotAfter -gt (Get-Date).AddDays(30) -and $_.Issuer -eq $_.Subject
        } | Sort-Object NotAfter -Descending | Select-Object -First 1
    $created = $false
    if (-not $certificate) {
        $certificate = New-SelfSignedCertificate -Type CodeSigningCert -Subject $subject `
            -FriendlyName $friendly -CertStoreLocation 'Cert:\CurrentUser\My' `
            -KeyAlgorithm RSA -KeyLength 3072 -HashAlgorithm SHA256 `
            -KeyUsage DigitalSignature -KeyExportPolicy NonExportable -NotAfter (Get-Date).AddYears(2)
        $created = $true
    }
    $publicPath = Join-Path $directory ($certificate.Thumbprint + '.cer')
    Export-Certificate -Cert $certificate -FilePath $publicPath -Force | Out-Null
    $result = [ordered]@{
        publisher = $Publisher.Trim(); subject = $certificate.Subject; thumbprint = $certificate.Thumbprint
        expires = $certificate.NotAfter.ToString('o'); public_certificate = $publicPath
        self_signed = $true; created = $created; store = 'CurrentUser\My'
    }
    $json = $result | ConvertTo-Json -Compress
    [System.IO.File]::WriteAllText($metadataPath, $json, [System.Text.UTF8Encoding]::new($false))
    if (-not $Quiet) { Write-Output ('EBS_JSON:' + $json) }
    exit 0
} catch {
    [Console]::Error.WriteLine('Certificate setup failed: ' + $_.Exception.Message)
    exit 1
}
