$ErrorActionPreference = 'Stop'
$setuRoot = Split-Path -Parent $PSScriptRoot
$setuTaskName = 'YojanaSetu-Telegram'
$setuScript = Join-Path $setuRoot 'scripts\run-telegram.ps1'
$setuArguments = '-NoProfile -NonInteractive -WindowStyle Hidden -File "' + $setuScript + '"'
$setuExisting = Get-ScheduledTask -TaskName $setuTaskName -ErrorAction SilentlyContinue
if ($setuExisting -and $setuExisting.Actions.Arguments -notcontains $setuArguments) {
    throw 'A different task already uses the name YojanaSetu-Telegram. Nothing was changed.'
}
$setuUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$setuAction = New-ScheduledTaskAction -Execute (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -Argument $setuArguments -WorkingDirectory $setuRoot
$setuTrigger = New-ScheduledTaskTrigger -AtLogOn -User $setuUser
$setuPrincipal = New-ScheduledTaskPrincipal -UserId $setuUser -LogonType Interactive -RunLevel Limited
$setuSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $setuTaskName -Action $setuAction -Trigger $setuTrigger -Principal $setuPrincipal -Settings $setuSettings -Description 'Run Yojana Setu Telegram after sign-in and restart after process failure. Requires an awake, connected computer.' -Force | Select-Object TaskName,State
Write-Output 'Task installed. Stop any existing manual polling process before starting this task.'
