#!/usr/bin/env bash
# Mac: dois cliques para instalar.
cd "$(dirname "$0")"
chmod +x instalar.sh emissor "Abrir Emissor.command" 2>/dev/null || true
./instalar.sh
