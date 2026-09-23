param(
    [string]$DesktopSource = (Join-Path $PSScriptRoot '..\Ngpcraft_emulator'),
    [string]$Emsdk = $env:EMSDK,
    [string]$Generator = 'Ninja',
    [string]$Make = ''
)
$ErrorActionPreference = 'Stop'
if ($Emsdk) {
    $emcmake = Join-Path $Emsdk 'upstream\emscripten\emcmake.bat'
    if (!(Test-Path -LiteralPath $emcmake)) { throw 'Emscripten not found. Activate emsdk or pass -Emsdk.' }
} else {
    $emcmake = (Get-Command emcmake -ErrorAction Stop).Source
}
if (!(Test-Path -LiteralPath (Join-Path $DesktopSource 'cpp\include\ngpc_core.h'))) {
    throw 'Desktop core not found. Clone Ngpcraft_emulator next to this project, or pass -DesktopSource.'
}
$configureArgs = @('cmake', '-S', $PSScriptRoot, '-B', "$PSScriptRoot/build", '-G', $Generator,
    "-DNGPCRAFT_DESKTOP=$DesktopSource", '-DCMAKE_BUILD_TYPE=Release')
if ($Make) { $configureArgs += "-DCMAKE_MAKE_PROGRAM=$Make" }
& $emcmake @configureArgs
if ($LASTEXITCODE) { throw 'CMake configuration failed.' }
cmake --build "$PSScriptRoot/build" --parallel
if ($LASTEXITCODE) { throw 'Compilation failed.' }
if (!$Emsdk) {
    # The SDK location is not needed for compiling, but packaging reads runtime notices.
    $emscripten = Split-Path -Parent $emcmake
} else { $emscripten = Join-Path $Emsdk 'upstream\emscripten' }
python "$PSScriptRoot/package.py" --desktop $DesktopSource --emscripten $emscripten
if ($LASTEXITCODE) { throw 'Packaging failed.' }
