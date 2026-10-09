$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
try {
    $request = [Console]::In.ReadToEnd() | ConvertFrom-Json
    switch ($request.action) {
        'ensure' {
            & (Join-Path $PSScriptRoot 'Ensure-Certificate.ps1') -Publisher ([string]$request.publisher)
            exit $LASTEXITCODE
        }
        'list' {
            $location = if ($request.machine_store) { 'Cert:\LocalMachine\My' } else { 'Cert:\CurrentUser\My' }
            $rows = @(Get-ChildItem $location -CodeSigningCert | Where-Object {
                $_.HasPrivateKey -and $_.NotBefore -le (Get-Date) -and $_.NotAfter -gt (Get-Date)
            } | ForEach-Object {
                [ordered]@{ thumbprint = $_.Thumbprint; subject = $_.Subject; expires = $_.NotAfter.ToString('o');
                    self_signed = ($_.Issuer -eq $_.Subject) }
            })
            Write-Output ('EBS_JSON:' + (ConvertTo-Json -InputObject $rows -Compress))
        }
        'import' {
            if (-not (Test-Path -LiteralPath $request.path -PathType Leaf)) { throw 'PFX file not found.' }
            # Password arrives through stdin, never argv, log, settings, or a temporary file.
            $secure = [System.Security.SecureString]::new()
            foreach ($character in ([string]$request.password).ToCharArray()) { $secure.AppendChar($character) }
            $secure.MakeReadOnly()
            $request.password = $null
            try { $imported = @(Import-PfxCertificate -FilePath $request.path -Password $secure -CertStoreLocation 'Cert:\CurrentUser\My') }
            finally { $secure.Dispose() }
            $certificate = $imported | Where-Object {
                $_.HasPrivateKey -and $_.NotBefore -le (Get-Date) -and $_.NotAfter -gt (Get-Date) -and
                ($_.EnhancedKeyUsageList.ObjectId -contains '1.3.6.1.5.5.7.3.3')
            } | Select-Object -First 1
            if (-not $certificate) { throw 'PFX contains no active Code Signing certificate with a private key.' }
            $result = [ordered]@{ thumbprint = $certificate.Thumbprint; subject = $certificate.Subject;
                expires = $certificate.NotAfter.ToString('o'); self_signed = ($certificate.Issuer -eq $certificate.Subject) }
            Write-Output ('EBS_JSON:' + ($result | ConvertTo-Json -Compress))
        }
        'install-sdk' {
            if (-not (Test-Path -LiteralPath $request.path -PathType Leaf)) { throw 'Select the downloaded Windows SDK installer.' }
            $signature = Get-AuthenticodeSignature -LiteralPath $request.path
            if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch '(^|,\s*)O=Microsoft Corporation(,|$)') {
                throw 'Use the original Microsoft-signed Windows SDK installer downloaded from Microsoft.'
            }
            Write-Output 'Finish the Windows SDK wizard and select Windows SDK Signing Tools for Desktop Apps.'
            $installer = Start-Process -FilePath $request.path -Verb RunAs -PassThru -Wait
            if ($installer.ExitCode -notin @(0,3010)) { throw ('SDK installer failed / cancelled: ' + $installer.ExitCode) }
            Write-Output ('EBS_JSON:' + (@{ installed = $true; restart_required = ($installer.ExitCode -eq 3010) } | ConvertTo-Json -Compress))
        }
        default { throw 'Unknown signing operation.' }
    }
    exit 0
} catch {
    [Console]::Error.WriteLine('Signing operation failed: ' + $_.Exception.Message)
    exit 1
}
