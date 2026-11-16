#!/usr/bin/env bash
# Mac: dois cliques para abrir o painel no navegador. Feche esta janela para desligar o emissor.
cd "$(dirname "$0")"
command -v uv >/dev/null 2>&1 || export PATH="$HOME/.local/bin:$PATH"
if [ ! -d .venv ]; then ./instalar.sh; exit; fi
uv run --quiet emissor painel
