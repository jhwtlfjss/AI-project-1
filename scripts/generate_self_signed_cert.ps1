param(
  [string]$DnsName = "my-companion-ai.local",
  [string]$OutDir = (Join-Path (Resolve-Path "$PSScriptRoot\..").Path "data\certs")
)

$ErrorActionPreference = "Stop"

function ConvertTo-Pem {
  param(
    [byte[]]$Bytes,
    [string]$Label
  )
  $base64 = [Convert]::ToBase64String($Bytes)
  $lines = New-Object System.Collections.Generic.List[string]
  $lines.Add("-----BEGIN $Label-----")
  for ($i = 0; $i -lt $base64.Length; $i += 64) {
    $length = [Math]::Min(64, $base64.Length - $i)
    $lines.Add($base64.Substring($i, $length))
  }
  $lines.Add("-----END $Label-----")
  return ($lines -join "`n") + "`n"
}

function Export-PrivateKeyDer {
  param($Rsa)
  try {
    return $Rsa.ExportPkcs8PrivateKey()
  } catch {
    if ($Rsa.Key) {
      return $Rsa.Key.Export([System.Security.Cryptography.CngKeyBlobFormat]::Pkcs8PrivateBlob)
    }
    throw
  }
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$rsa = [System.Security.Cryptography.RSA]::Create(2048)
$hash = [System.Security.Cryptography.HashAlgorithmName]::SHA256
$padding = [System.Security.Cryptography.RSASignaturePadding]::Pkcs1
$request = [System.Security.Cryptography.X509Certificates.CertificateRequest]::new(
  "CN=$DnsName",
  $rsa,
  $hash,
  $padding
)

$san = [System.Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder]::new()
$san.AddDnsName($DnsName)
$request.CertificateExtensions.Add($san.Build())
$request.CertificateExtensions.Add(
  [System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($false, $false, 0, $true)
)
$request.CertificateExtensions.Add(
  [System.Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new(
    [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::DigitalSignature,
    $true
  )
)

$cert = $request.CreateSelfSigned([DateTimeOffset]::Now.AddDays(-1), [DateTimeOffset]::Now.AddYears(5))

$certDer = $cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert)
$keyDer = Export-PrivateKeyDer -Rsa $rsa
$certPem = ConvertTo-Pem -Bytes $certDer -Label "CERTIFICATE"
$keyPem = ConvertTo-Pem -Bytes $keyDer -Label "PRIVATE KEY"

$certPath = Join-Path $OutDir "server.crt.pem"
$keyPath = Join-Path $OutDir "server.key.pem"
Set-Content -Path $certPath -Value $certPem -Encoding ascii
Set-Content -Path $keyPath -Value $keyPem -Encoding ascii

Write-Host "Certificate: $certPath"
Write-Host "Private key:  $keyPath"
Write-Host "Use with:"
Write-Host "python scripts/serve_lan.py --host 0.0.0.0 --port 8765 --live-web --ssl-cert `"$certPath`" --ssl-key `"$keyPath`""
