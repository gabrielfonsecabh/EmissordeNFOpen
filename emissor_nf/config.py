"""Caminhos, ambientes e constantes."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import __version__

PACOTE = Path(__file__).resolve().parent
RAIZ = PACOTE.parent
DIR_SCHEMAS = PACOTE / "schemas"
DIR_FONTES = PACOTE / "fontes"

# Tudo que é seu (banco, certificados, notas, logs) fica em dados/, fora do git.
# Para guardar em outro lugar (ex.: uma pasta do Google Drive), defina EMISSOR_DADOS.
DIR_DADOS = Path(os.environ.get("EMISSOR_DADOS") or (RAIZ / "dados")).expanduser().resolve()


def resolver(caminho: str | Path) -> Path:
    """Caminho gravado no banco que aponta para dentro de dados/. Se a pasta mudou de lugar
    (backup restaurado, outro computador), procura o mesmo arquivo na pasta de dados atual."""
    p = Path(caminho)
    if p.exists() or "dados" not in p.parts:
        return p
    i = len(p.parts) - 1 - p.parts[::-1].index("dados")
    alternativo = DIR_DADOS.joinpath(*p.parts[i + 1:])
    return alternativo if alternativo.exists() else p


def dir_dados(*partes: str) -> Path:
    p = DIR_DADOS.joinpath(*partes)
    p.mkdir(parents=True, exist_ok=True)
    return p


ARQ_BANCO = DIR_DADOS / "emissor.db"

# Horário de Brasília (sem horário de verão desde 2019). A DPS exige o fuso explícito.
TZ = timezone(timedelta(hours=-3), "BRT")

PRODUCAO = "1"
HOMOLOGACAO = "2"
AMBIENTES = {PRODUCAO: "Produção", HOMOLOGACAO: "Homologação (teste, sem valor fiscal)"}

URL_SEFIN = {
    PRODUCAO: "https://sefin.nfse.gov.br/SefinNacional",
    HOMOLOGACAO: "https://sefin.producaorestrita.nfse.gov.br/SefinNacional",
}
URL_CONSULTA_PUBLICA = "https://www.nfse.gov.br/ConsultaPublica/?tpc=1&chave={chave}"

# Nota Técnica 009: vale na Produção Restrita desde 20/10/2026 e na Produção a partir de 01/12/2026.
INICIO_NT009_PRODUCAO = datetime(2026, 12, 1, tzinfo=TZ)

# verAplic aceita até 20 caracteres.
VERSAO_APLICATIVO = f"EmissorNFOpen_{__version__}"[:20]

KEYRING_SERVICO = "emissor-nf-open"

MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def agora() -> datetime:
    return datetime.now(TZ).replace(microsecond=0)


def nome_ambiente(tp_amb: str) -> str:
    return AMBIENTES.get(tp_amb, tp_amb)
