# Instalador do Emissor de NF Open Source (Windows). Feito pela TechZyon.
# Pode rodar quantas vezes quiser: ele so instala o que falta.
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host ""
Write-Host "  Emissor de NF Open Source - TechZyon (techzyon.com.br)"
Write-Host "  Instalando. Isso leva de 1 a 3 minutos na primeira vez."
Write-Host ""

$uvLocal = Join-Path $env:USERPROFILE ".local\bin"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    if (Test-Path (Join-Path $uvLocal "uv.exe")) { $env:Path = "$uvLocal;$env:Path" }
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "> Instalando o uv (gerenciador de Python, gratuito, da Astral)..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$uvLocal;$env:Path"
}

Write-Host "> Preparando o Python e as bibliotecas..."
uv sync --quiet

Write-Host "> Conferindo se esta tudo funcionando..."
uv run --quiet python -m pytest -q --no-header -p no:cacheprovider | Select-Object -Last 1

Write-Host "> Gerando um PDF de exemplo..."
uv run --quiet emissor exemplo

Write-Host ""
Write-Host "  Pronto! Para abrir o emissor, de dois cliques em 'Abrir Emissor.bat'."
Write-Host ""
if ($args -notcontains "--sem-abrir") { uv run emissor painel }
