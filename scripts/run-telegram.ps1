$ErrorActionPreference = 'Stop'
$setuRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $setuRoot
New-Item -ItemType Directory -Path (Join-Path $setuRoot 'artifacts') -Force | Out-Null
& (Join-Path $setuRoot '.venv\Scripts\python.exe') -u -m bot.telegram_polling 1>> (Join-Path $setuRoot 'artifacts\telegram.log') 2>> (Join-Path $setuRoot 'artifacts\telegram.err')
exit $LASTEXITCODE
