$ErrorActionPreference = "Stop"

$secureKey = Read-Host "Paste your HeyGen API key" -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

try {
    $plainKey = ([Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)).Trim()
    if ([string]::IsNullOrWhiteSpace($plainKey)) {
        throw "The API key cannot be empty."
    }

    [Environment]::SetEnvironmentVariable("HEYGEN_API_KEY", $plainKey, "User")
    $env:HEYGEN_API_KEY = $plainKey
    Write-Host "HEYGEN_API_KEY is configured for the current Windows user."
}
finally {
    if ($pointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
    Remove-Variable plainKey -ErrorAction SilentlyContinue
    Remove-Variable secureKey -ErrorAction SilentlyContinue
}
