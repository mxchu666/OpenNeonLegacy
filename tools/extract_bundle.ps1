#!/usr/bin/env powershell
<#
.SYNOPSIS
  Extracts the NEONBND2 single-file bundle out of neon_legacy.exe.
.DESCRIPTION
  Parses the 80-byte footer, reads the entry table, carves each zstd frame and
  decompresses it with 7-Zip (zstd codec) or the zstd CLI. Verified against the
  sample bundle: 12/12 entries extracted with exact sizes.
.NOTES
  Requires: 7-Zip >= 21 (zstd support) or zstd.exe on PATH.
#>
param(
    [Parameter(Mandatory = $true)][string]$Bundle,
    [string]$OutDir = (Join-Path (Get-Location) 'extracted')
)

$ErrorActionPreference = 'Stop'

$fs = [IO.File]::OpenRead($Bundle)
$len = $fs.Length

# --- footer ---
$fs.Position = $len - 80
$foot = New-Object byte[] 80
$null = $fs.Read($foot, 0, 80)
$magic = [Text.Encoding]::ASCII.GetString($foot, 0, 8)
if ($magic -ne 'NEONBND2') { throw "bad bundle magic: $magic" }
$tableAbs = [BitConverter]::ToInt64($foot, 8)
$identity = [Text.Encoding]::ASCII.GetString($foot, 16, 64)
Write-Host "table @ 0x$($tableAbs.ToString('X'))  identity=$identity"

# --- entry table ---
$tableLen = ($len - 80) - $tableAbs
if ($tableLen -lt 4) { throw "invalid table length $tableLen" }
$tbl = New-Object byte[] $tableLen
$fs.Position = $tableAbs
$null = $fs.Read($tbl, 0, $tableLen)

$pos = 0
$count = [BitConverter]::ToUInt32($tbl, $pos); $pos += 4
Write-Host "entries: $count"
$entries = @()
for ($i = 0; $i -lt $count; $i++) {
    $plen = [BitConverter]::ToInt32($tbl, $pos); $pos += 4
    if ($plen -lt 1 -or $plen -gt 2048) { throw "bad path length at entry $i" }
    $p = [Text.Encoding]::ASCII.GetString($tbl, $pos, $plen); $pos += $plen
    $off  = [BitConverter]::ToInt64($tbl, $pos)
    $comp = [BitConverter]::ToInt64($tbl, $pos + 8)
    $uncomp = [BitConverter]::ToInt64($tbl, $pos + 16)
    $pos += 24
    $entries += [pscustomobject]@{ Path = $p; Offset = $off; Comp = $comp; Uncomp = $uncomp }
    Write-Host ("  {0,-22} off=0x{1:X} comp={2} uncomp={3}" -f $p, $off, $comp, $uncomp)
}
$fs.Close()

if ($pos -ne $tableLen) { Write-Warning "table leftover bytes: $($tableLen - $pos)" }

# --- carve + decompress ---
$zip = Get-Command 7z -ErrorAction SilentlyContinue
if (-not $zip) { $zip = Get-Command zstd -ErrorAction SilentlyContinue }
if (-not $zip) { throw "need 7-Zip (with zstd codec) or zstd.exe on PATH" }

$tmp = Join-Path $env:TEMP ("neonbnd_" + [IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Force -Path $tmp, $OutDir | Out-Null

foreach ($e in $entries) {
    $zst = Join-Path $tmp ([IO.Path]::GetFileName($e.Path) + '.zst')
    $in = [IO.File]::OpenRead($Bundle)
    $in.Position = $e.Offset
    $outf = [IO.File]::Create($zst)
    $chunk = New-Object byte[] (16MB)
    $left = $e.Comp
    while ($left -gt 0) {
        $n = [int][Math]::Min($left, $chunk.Length)
        $r = $in.Read($chunk, 0, $n)
        if ($r -le 0) { throw "unexpected EOF carving $($e.Path)" }
        $outf.Write($chunk, 0, $r)
        $left -= $r
    }
    $outf.Close(); $in.Close()

    $destDir = Join-Path $OutDir ([IO.Path]::GetDirectoryName($e.Path))
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null
    $destFile = Join-Path $destDir ([IO.Path]::GetFileName($e.Path))

    if ($zip.Name -eq '7z') {
        $null = & 7z x -y "-o$destDir" $zst 2>&1 | Select-Object -Last 2
    } else {
        & zstd -d -f -o $destFile $zst
    }
    Remove-Item $zst -Force

    $got = (Get-Item $destFile).Length
    $ok = if ($got -eq $e.Uncomp) { 'OK' } else { 'MISMATCH' }
    Write-Host ("  -> {0} ({1} bytes) {2}" -f $destFile, $got, $ok)
}

Remove-Item $tmp -Recurse -Force
Write-Host "done: $OutDir"
