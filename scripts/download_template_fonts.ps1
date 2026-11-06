# Re-download OFL variable fonts used by template PIL renderer (google/fonts main branch).
$ErrorActionPreference = "Stop"
$dest = Join-Path $PSScriptRoot "..\backend\static\fonts"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$urls = @{
  "VazirmatnVF.ttf" = "https://raw.githubusercontent.com/google/fonts/main/ofl/vazirmatn/Vazirmatn%5Bwght%5D.ttf"
  "InterVF.ttf"     = "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf"
}
foreach ($name in $urls.Keys) {
  $out = Join-Path $dest $name
  Write-Host "Downloading $name ..."
  Invoke-WebRequest -Uri $urls[$name] -OutFile $out -UseBasicParsing
}
Write-Host "Done. Files:" 
Get-ChildItem $dest -Filter "*.ttf" | Select-Object Name, Length
