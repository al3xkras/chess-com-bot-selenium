#Requires -Version 5.1

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptDir = (Resolve-Path $ScriptDir).Path
Set-Location $ScriptDir

$EnvFileName = "config.env"
$ComposeFile = (Resolve-Path ".\docker\docker-compose.yml").Path

function Import-DotEnv {
    param(
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        return
    }

    Write-Host "Loading configuration from $Path"

    foreach ($line in Get-Content $Path) {

        $line = $line.Trim()

        if ($line -eq "") { continue }
        if ($line.StartsWith("#")) { continue }

        $parts = $line -split "=",2

        if ($parts.Count -ne 2) {
            continue
        }

        $name = $parts[0].Trim()
        $value = $parts[1].Trim()

        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))) {

            $value = $value.Substring(1,$value.Length-2)
        }

        [Environment]::SetEnvironmentVariable($name,$value,"Process")
    }
}

Import-DotEnv (Join-Path $ScriptDir $EnvFileName)

function Test-True {
    param([string]$Value)

    switch ($Value.ToLower()) {
        "1"     { return $true }
        "true"  { return $true }
        "0"     { return $false }
        "false" { return $false }
        default {
            throw "Invalid boolean value: $Value"
        }
    }
}

function Get-EnvValue {
    param(
        [string]$Name,
        $Default
    )

    $value = [Environment]::GetEnvironmentVariable($Name)

    if ([string]::IsNullOrWhiteSpace($value)) {
        return $Default
    }

    return $value
}

function Start-Local {

    $elo = Get-EnvValue "ELO_RATING" "-1"
    $timer = Get-EnvValue "GAME_TIMER_MS" "150000"
    $firstMove = Get-EnvValue "FIRST_MOVE_W" "e2e4"

    $stockfishVersion = Get-EnvValue "STOCKFISH_VERSION" "sf_18"
    $stockfishArchive = Get-EnvValue "STOCKFISH_ARCHIVE" "stockfish-windows-x86-64.zip"

    $stockfishUrl = Get-EnvValue `
        "STOCKFISH_URL" `
        "https://github.com/official-stockfish/Stockfish/releases/download/$stockfishVersion/$stockfishArchive"

    $venv = Join-Path $ScriptDir "venv"
    $python = Join-Path $venv "Scripts\python.exe"
    $pip = Join-Path $venv "Scripts\pip.exe"

    $stockfishDir = Join-Path $ScriptDir "stockfish"
    $stockfishExe = Join-Path $stockfishDir "stockfish.exe"

    #
    # Virtual environment
    #

    if (-not (Test-Path $venv)) {

        Write-Host "Creating virtual environment..."

        python -m venv $venv

        & $pip install -r (Join-Path $ScriptDir "requirements.txt")
    }

    New-Item -ItemType Directory -Force -Path $stockfishDir | Out-Null

    #
    # Stockfish
    #

    if (-not (Test-Path $stockfishExe)) {



        $archive = Join-Path $ScriptDir $stockfishArchive
        Write-Host "Downloading Stockfish... $stockfishUrl"
        Write-Host "Archive name: $archive"

        Invoke-WebRequest `
            -Uri $stockfishUrl `
            -OutFile $archive

        Expand-Archive `
            -Path $archive `
            -DestinationPath ./ `
            -Force

        $downloadedExe = Get-ChildItem `
            -Recurse `
            -Filter "stockfish*.exe" |
            Select-Object -First 1

        if (-not $downloadedExe) {
            throw "Unable to locate Stockfish executable."
        }

        Move-Item $downloadedExe.FullName $stockfishExe -Force

        Remove-Item $archive
    }

    & $python `
        src/main.py `
        --elo-rating $elo `
        --game-timer-ms $timer `
        --first-move-w $firstMove `
        --enable-move-delay $env:ENABLE_MOVE_DELAY `
        --next-game-auto $env:START_NEW_GAME_AUTOMATICALLY `
        --autostart $env:AUTOSTART_FIRST_GAME `
        --game-type $env:GAME_TYPE
}

function Start-Docker {
 
    if ((Test-True $env:OPEN_BROWSER) -and ($ComposeArgs -contains "up")) {

        Write-Host "Opening container URLs automatically"

        Start-Job -InitializationScript {
            function Wait-ForPort {
                param([int]$Port)

                Write-Host "Waiting for localhost:$Port..."

                while (-not (Test-NetConnection -ComputerName localhost -Port $Port -InformationLevel Quiet)) {
                    Start-Sleep -Milliseconds 500
                }

                Write-Host "Port $Port is reachable."
            }

            function Open-Port {
                param([int]$Port)
                
                Wait-ForPort $Port

                Start-Process "http://localhost:$Port"
            }

            function Open-PortsInBrowser {

                $ports = $env:REPLICA_PORTS

                if ([string]::IsNullOrWhiteSpace($ports)) {
                    throw "REPLICA_PORTS is not set"
                }

                if ($ports -match '^(\d+)-(\d+)$') {

                    $start = [int]$Matches[1]
                    $end = [int]$Matches[2]

                    if ($start -gt $end) {
                        throw "Invalid range ($start > $end)"
                    }

                    foreach ($p in $start..$end) {
                        Open-Port $p
                    }
                }
                elseif ($ports -match '^\d+$') {

                    Open-Port ([int]$ports)

                }
                else {

                    throw "REPLICA_PORTS must be a single port or a range."

                }
            }
        } -ScriptBlock {
            Open-PortsInBrowser
        }
    }

    Write-Host "Compose args: $ComposeArgs"
    Write-Host "Compose file: $ComposeFile"

    docker compose -f $ComposeFile @ComposeArgs

}

#
# Main
#

$ComposeArgs = $args

if ($ComposeArgs.Count -eq 0) {
    $ComposeArgs = @("up","--build")
}

Write-Host ARGS $ComposeArgs ($ComposeArgs -contains "up") $env:OPEN_BROWSER ((Test-True $env:OPEN_BROWSER) -and ($ComposeArgs -contains "up"))

switch ($env:STARTUP_TYPE) {

    "docker" {
        Start-Docker
    }

    "local" {
        Start-Local
    }

    default {
        throw "Unknown startup type: $($env:STARTUP_TYPE). Possible values: docker / local"
    }
}