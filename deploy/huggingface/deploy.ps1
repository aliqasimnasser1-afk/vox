<#
  Publish this project to a Hugging Face Space (Docker) as a second server.

  Before running:
    1. Create a free account at https://huggingface.co (no card needed).
    2. Create a Space: New -> Space, SDK = Docker, Blank, hardware "CPU basic" (free). Leave it empty.
    3. Create an access token with WRITE permission: Settings -> Access Tokens.

  Run from the project root:
    powershell -ExecutionPolicy Bypass -File deploy\huggingface\deploy.ps1 -User YOUR_HF_USERNAME -Space vox

  Git will ask for your username and password: type your HF username and paste the TOKEN as the password.
  The token is typed by you in your own terminal; this script never stores it.
#>
param(
  [Parameter(Mandatory = $true)][string]$User,
  [string]$Space = "vox"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..\..").Path
$work = Join-Path $env:TEMP ("vox-hf-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
$remote = "https://huggingface.co/spaces/$User/$Space"

Write-Host "Cloning $remote ..."
git clone $remote $work
if ($LASTEXITCODE -ne 0) { throw "Could not clone the Space. Check the username, space name and token." }

Write-Host "Exporting the committed project..."
Push-Location $root
git archive HEAD | tar -x -C $work
Pop-Location

# Space-specific Dockerfile and README (the one with the metadata block Spaces require).
Copy-Item "$root\deploy\huggingface\Dockerfile" "$work\Dockerfile" -Force
Copy-Item "$root\deploy\huggingface\SPACE_README.md" "$work\README.md" -Force
Remove-Item "$work\render.yaml", "$work\.dockerignore" -ErrorAction SilentlyContinue

Push-Location $work
git add -A
git -c user.name="$User" -c user.email="$User@users.noreply.huggingface.co" commit -m "Deploy Vox" | Out-Null
git push
Pop-Location

Write-Host ""
Write-Host "Done. The Space builds for a few minutes. Open it at:"
Write-Host "  https://$User-$Space.hf.space   (direct URL, use this one)"
Write-Host "  $remote"
