<#
Lab scan (run on the SCANNER laptop, in PowerShell "Run as administrator").

Uses the same nmap flags as the Validation Set files, plus the lab ports,
rate-limited to 100 packets/second (rules of engagement).
Saves the XML into data/lab/<Name>.xml.

Example:
  powershell -ExecutionPolicy Bypass -File lab\scan.ps1 -Subnet 172.20.10.0/28 -Name scan_01_before -IOwnThisNetwork
#>
param(
    [Parameter(Mandatory = $true)] [string]$Subnet,
    [Parameter(Mandatory = $true)] [string]$Name,
    [switch]$IOwnThisNetwork
)

$ErrorActionPreference = "Stop"

# 1. Explicit consent
if (-not $IOwnThisNetwork) {
    Write-Host "Refused: add -IOwnThisNetwork to confirm this is your own hotspot subnet." -ForegroundColor Red
    exit 1
}

# 2. Only private ranges, max /24 (you must still be connected to the hotspot only)
if ($Subnet -notmatch '^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/(\d{1,2})$') {
    Write-Host "Refused: subnet must look like 172.20.10.0/28" -ForegroundColor Red
    exit 1
}
$a = [int]$Matches[1]; $b = [int]$Matches[2]; $prefix = [int]$Matches[5]
$private = ($a -eq 10) -or ($a -eq 172 -and $b -ge 16 -and $b -le 31) -or ($a -eq 192 -and $b -eq 168)
if (-not $private) {
    Write-Host "Refused: $Subnet is not a private range." -ForegroundColor Red
    exit 1
}
if ($prefix -lt 24) {
    Write-Host "Refused: /$prefix is too big for the lab. Use /24 or smaller (e.g. /28)." -ForegroundColor Red
    exit 1
}

# 3. Administrator rights (needed for -sS / -sU)
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Write-Host "Run PowerShell as administrator (needed for the SYN and UDP scan)." -ForegroundColor Red
    exit 1
}

if (-not (Get-Command nmap -ErrorAction SilentlyContinue)) {
    Write-Host "nmap not found. Install it from https://nmap.org/download.html" -ForegroundColor Red
    exit 1
}

# 4. Scan
$outDir = Join-Path $PSScriptRoot "..\data\lab"
New-Item -ItemType Directory -Force $outDir | Out-Null
$outFile = Join-Path $outDir "$Name.xml"

$ports = "T:1-1000,1883,2121,2222,2323,6379,8080,U:53,123,161,1900,5353"
Write-Host "Scanning $Subnet -> $outFile (this takes a few minutes)"
nmap -sS -sU -sV --script http-title --max-rate 100 -p $ports -oX $outFile $Subnet

Write-Host "Saved $outFile" -ForegroundColor Green
