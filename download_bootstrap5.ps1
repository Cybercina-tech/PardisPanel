# Download Bootstrap 5.3.3 (Latest stable version)
$bootstrapVersion = "5.3.3"
$baseUrl = "https://cdn.jsdelivr.net/npm/bootstrap@$bootstrapVersion/dist"

# Create directories if they don't exist
$cssDir = "static\css"
$jsDir = "static\js"

if (-not (Test-Path $cssDir)) {
    New-Item -ItemType Directory -Path $cssDir -Force
}
if (-not (Test-Path $jsDir)) {
    New-Item -ItemType Directory -Path $jsDir -Force
}

# Download Bootstrap CSS
Write-Host "Downloading Bootstrap CSS..."
$cssUrl = "$baseUrl/css/bootstrap.min.css"
$cssPath = "$cssDir\bootstrap.min.css"
Invoke-WebRequest -Uri $cssUrl -OutFile $cssPath
Write-Host "Bootstrap CSS downloaded to $cssPath"

# Download Bootstrap JS Bundle (includes Popper.js)
Write-Host "Downloading Bootstrap JS Bundle..."
$jsUrl = "$baseUrl/js/bootstrap.bundle.min.js"
$jsPath = "$jsDir\bootstrap.bundle.min.js"
Invoke-WebRequest -Uri $jsUrl -OutFile $jsPath
Write-Host "Bootstrap JS Bundle downloaded to $jsPath"

Write-Host "`nBootstrap 5.3.3 download complete!"
Write-Host "Files are ready to use in your project."

