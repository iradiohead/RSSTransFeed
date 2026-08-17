[CmdletBinding()]
param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Torch contains deeply nested license files. Keep the build environment out of
# the already long OneDrive project path to stay below Windows path limits.
$buildEnvironment = Join-Path $env:LOCALAPPDATA "RSSTransFeed2-build"
$venvPython = Join-Path $buildEnvironment "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating isolated build environment..."
    & $Python -m venv $buildEnvironment
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the build environment with '$Python'."
    }
}

Write-Host "Installing application and packaging dependencies..."
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to update pip." }

& $venvPython -m pip install -r "requirements.txt" -r "requirements-build.txt"
if ($LASTEXITCODE -ne 0) { throw "Failed to install build dependencies." }

Write-Host "Running tests..."
& $venvPython -m pip install pytest
if ($LASTEXITCODE -ne 0) { throw "Failed to install pytest." }

& $venvPython -m pytest
if ($LASTEXITCODE -ne 0) { throw "Tests failed; release build stopped." }

Remove-Item "build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "dist" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Building standalone application..."
& $venvPython -m PyInstaller --noconfirm --clean "RSSTransFeed.spec"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

$archive = Join-Path $PSScriptRoot "dist\RSSTransFeed-windows-x64.zip"
Write-Host "Creating release archive..."
Compress-Archive -Path "dist\RSSTransFeed" -DestinationPath $archive -CompressionLevel Optimal

Write-Host ""
Write-Host "Release ready:"
Write-Host "  $archive"
Write-Host "Users can extract the ZIP and run RSSTransFeed.exe; Python is not required."
