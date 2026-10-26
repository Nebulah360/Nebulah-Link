$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$project = Join-Path $repo 'vendor\BadBuilder\BadBuilder\BadBuilder.csproj'
$output = Join-Path $repo '.local\badbuilder'
$localDotnet = Join-Path $repo '.local\dotnet\dotnet.exe'
$dotnet = if ($env:NEBULAH_DOTNET) { $env:NEBULAH_DOTNET } elseif (Test-Path -LiteralPath $localDotnet) { $localDotnet } else { (Get-Command dotnet.exe -ErrorAction Stop).Source }

$intermediate = Join-Path $repo '.local\badbuilder-obj\'
$compiled = Join-Path $repo '.local\badbuilder-bin\'
& $dotnet publish $project -c Release -r win-x64 --self-contained true -o $output `
  "-p:BaseIntermediateOutputPath=$intermediate" "-p:BaseOutputPath=$compiled"
if ($LASTEXITCODE -ne 0) { throw 'BadBuilder publish failed.' }

$dotnetHome = Split-Path -Parent $dotnet
Copy-Item -LiteralPath $dotnet -Destination (Join-Path $output 'dotnet.exe') -Force
$hostFxr = Join-Path $dotnetHome 'host\fxr'
if (-not (Test-Path -LiteralPath $hostFxr)) { throw '.NET host/fxr is missing.' }
New-Item -ItemType Directory -Path (Join-Path $output 'host\fxr') -Force | Out-Null
Copy-Item -Path (Join-Path $hostFxr '*') -Destination (Join-Path $output 'host\fxr') -Recurse -Force
Write-Host "BadBuilder web engine built at $output"
