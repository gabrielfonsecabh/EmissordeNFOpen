"""Banco local (SQLite, um arquivo em dados/emissor.db). Nada vai para a nuvem.

Modelo:
  certificados   arquivos .pfx importados (a senha fica no cofre do sistema, não aqui)
  empresas       quem emite (prestador). Um contador cadastra uma por cliente dele
  clientes       tomadores de cada empresa
  servicos       serviços de cada empresa, com os códigos fiscais já resolvidos
  modelos        "selecionar e emitir": cliente + serviço + valor + texto padrão
  emissoes       toda tentativa de emissão, com os dados congelados no momento do envio
  numeracao      próximo número da DPS por empresa, ambiente e série
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from . import config as C

ESQUEMA = """
create table if not exists certificados (
  id            integer primary key,
  apelido       text not null,
  arquivo       text not null,
  documento     text,
  titular       text,
  valido_ate    text,
  impressao     text unique,
  criado_em     text not null default (datetime('now'))
);

create table if not exists empresas (
  id                       integer primary key,
  apelido                  text not null,
  cnpj                     text not null unique,
  razao_social             text not null,
  nome_fantasia            text,
  inscricao_municipal      text,
  cod_municipio            text not null check (length(cod_municipio) = 7),
  municipio                text not null,
  uf                       text not null check (length(uf) = 2),
  logradouro               text,
  numero                   text,
  complemento              text,
  bairro                   text,
  cep                      text,
  telefone                 text,
  email                    text,
  -- regTrib da DPS: 1 não optante, 2 MEI, 3 ME/EPP do Simples Nacional
  opcao_simples            text not null default '3' check (opcao_simples in ('1','2','3')),
  regime_apuracao_simples  text default '1',
  regime_especial          text not null default '0',
  -- série própria do emissor: 1 a 49999 (70000+ é do Emissor Web do governo)
  serie_dps                integer not null default 1 check (serie_dps between 1 and 49999),
  certificado_id           integer references certificados(id) on delete set null,
  pasta_saida              text,
  marca_json               text,
  ativo                    integer not null default 1,
  criado_em                text not null default (datetime('now'))
);

create table if not exists clientes (
  id             integer primary key,
  empresa_id     integer not null references empresas(id) on delete cascade,
  tipo_doc       text not null check (tipo_doc in ('CNPJ','CPF')),
  documento      text not null,
  razao_social   text not null,
  email          text,
  telefone       text,
  cod_municipio  text not null check (length(cod_municipio) = 7),
  municipio      text,
  uf             text,
  cep            text not null,
  logradouro     text not null,
  numero         text not null,
  complemento    text,
  bairro         text not null,
  ativo          integer not null default 1,
  criado_em      text not null default (datetime('now')),
  unique (empresa_id, documento)
);

create table if not exists servicos (
  id                  integer primary key,
  empresa_id          integer not null references empresas(id) on delete cascade,
  nome                text not null,
  cod_trib_nacional   text not null check (length(cod_trib_nacional) = 6),
  cod_trib_municipal  text,
  cod_nbs             text,
  descricao_padrao    text,
  valor_padrao        text,
  cod_local_prestacao text,
  trib_issqn          text not null default '1',
  tp_ret_issqn        text not null default '1',
  cst_pis_cofins      text,
  tp_ret_pis_cofins   text,
  perc_trib_sn        text,
  ativo               integer not null default 1,
  criado_em           text not null default (datetime('now'))
);

create table if not exists modelos (
  id                integer primary key,
  empresa_id        integer not null references empresas(id) on delete cascade,
  nome              text not null,
  cliente_id        integer not null references clientes(id) on delete cascade,
  servico_id        integer not null references servicos(id) on delete cascade,
  valor             text not null,
  valor_minimo      text,
  valor_maximo      text,
  descricao_modelo  text not null,
  ativo             integer not null default 1,
  criado_em         text not null default (datetime('now')),
  unique (empresa_id, nome)
);

create table if not exists numeracao (
  empresa_id  integer not null references empresas(id) on delete cascade,
  ambiente    text not null,
  serie       integer not null,
  proximo     integer not null default 1,
  primary key (empresa_id, ambiente, serie)
);

create table if not exists emissoes (
  id              integer primary key,
  empresa_id      integer not null references empresas(id),
  certificado_id  integer references certificados(id) on delete set null,
  cliente_id      integer references clientes(id) on delete set null,
  servico_id      integer references servicos(id) on delete set null,
  modelo_id       integer references modelos(id) on delete set null,
  ambiente        text not null,
  status          text not null check (status in ('processando','emitida','rejeitada','verificar')),
  valor           text not null,
  descricao       text not null,
  mes_referencia  text,
  competencia     text,
  snapshot_json   text not null,
  serie           integer,
  n_dps           integer,
  id_dps          text,
  chave           text unique,
  numero_nfse     text,
  dh_emissao      text,
  xml_path        text,
  pdf_path        text,
  mensagens_json  text not null default '[]',
  tentativas      integer not null default 0,
  criado_em       text not null default (datetime('now')),
  atualizado_em   text not null default (datetime('now')),
  unique (empresa_id, ambiente, serie, n_dps)
);
create index if not exists emissoes_empresa on emissoes (empresa_id, id);
"""


def conectar(caminho: Path | str | None = None) -> sqlite3.Connection:
    caminho = Path(caminho or C.ARQ_BANCO)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(caminho, isolation_level=None, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma foreign_keys = on")
    conn.execute("pragma journal_mode = wal")
    conn.executescript(ESQUEMA)
    return conn


@contextmanager
def transacao(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """BEGIN IMMEDIATE: trava a escrita na hora, então dois envios simultâneos nunca pegam o mesmo número."""
    conn.execute("begin immediate")
    try:
        yield conn
    except BaseException:
        conn.execute("rollback")
        raise
    conn.execute("commit")


def linha(r: sqlite3.Row | None) -> dict | None:
    return dict(r) if r is not None else None


def obter(conn, tabela: str, id_: int) -> dict | None:
    return linha(conn.execute(f"select * from {tabela} where id = ?", (id_,)).fetchone())


def listar(conn, tabela: str, **filtros: Any) -> list[dict]:
    where = " and ".join(f"{k} = ?" for k in filtros) or "1=1"
    rows = conn.execute(f"select * from {tabela} where {where} order by id", tuple(filtros.values()))
    return [dict(r) for r in rows]


def inserir(conn, tabela: str, dados: dict) -> int:
    cols = ", ".join(dados)
    marc = ", ".join("?" for _ in dados)
    cur = conn.execute(f"insert into {tabela} ({cols}) values ({marc})", tuple(dados.values()))
    return int(cur.lastrowid)


def atualizar(conn, tabela: str, id_: int, dados: dict) -> None:
    if not dados:
        return
    sets = ", ".join(f"{k} = ?" for k in dados)
    cur = conn.execute(f"update {tabela} set {sets} where id = ?", (*dados.values(), id_))
    if cur.rowcount != 1:
        raise LookupError(f"{tabela} {id_} não encontrado")


def para_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def de_json(texto: str | None, padrao: Any = None) -> Any:
    if not texto:
        return padrao
    return json.loads(texto)
