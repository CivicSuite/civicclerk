$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Split-Path -Parent (Split-Path -Parent $ScriptRoot)

Set-Location $AppRoot
& (Join-Path $ScriptRoot "prereq-check.ps1")
& (Join-Path $AppRoot "install.ps1")
