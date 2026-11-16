#!/usr/bin/env bash
# Instalador do Emissor de NF Open Source (Mac e Linux). Feito pela TechZyon.
# Pode rodar quantas vezes quiser: ele só instala o que falta.
set -euo pipefail
cd "$(dirname "$0")"

echo ""
echo "  Emissor de NF Open Source · TechZyon (techzyon.com.br)"
echo "  Instalando. Isso leva de 1 a 3 minutos na primeira vez."
echo ""

if ! command -v uv >/dev/null 2>&1 && [ -x "$HOME/.local/bin/uv" ]; then
  export PATH="$HOME/.local/bin:$PATH"
fi
if ! command -v uv >/dev/null 2>&1; then
  echo "> Instalando o uv (gerenciador de Python, gratuito, da Astral)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "> Preparando o Python e as bibliotecas..."
uv sync --quiet

echo "> Conferindo se está tudo funcionando..."
uv run --quiet python -m pytest -q --no-header -p no:cacheprovider 2>&1 | tail -1

echo "> Gerando um PDF de exemplo..."
uv run --quiet emissor exemplo

chmod +x emissor "Abrir Emissor.command" 2>/dev/null || true

echo ""
echo "  Pronto! Para abrir o emissor:"
echo "    Mac: dê dois cliques em \"Abrir Emissor.command\""
echo "    Terminal: ./emissor painel"
echo ""
if [ "${1:-}" != "--sem-abrir" ]; then
  exec uv run emissor painel
fi
