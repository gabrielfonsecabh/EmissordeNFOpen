"""Perfis: exportar e importar uma empresa com clientes, serviços e modelos (JSON).

Serve para o contador montar o "template" de cada cliente dele uma vez, guardar, mandar para
outro computador ou compartilhar com a equipe. O certificado e a senha NUNCA entram no perfil.
"""

from __future__ import annotations

import base64
from pathlib import Path

from . import config as C
from . import db

VERSAO_PERFIL = 1
LOGO_MAX = 2 * 1024 * 1024


def _marca_para_perfil(marca_json: str | None) -> str | None:
    """Troca o caminho local do logo pelo próprio arquivo (base64), para o perfil funcionar em outro computador."""
    marca = db.de_json(marca_json) if marca_json else None
    if not marca:
        return marca_json
    caminho = marca.pop("logo", None)
    if caminho and Path(caminho).is_file() and Path(caminho).stat().st_size <= LOGO_MAX:
        marca["logo_arquivo"] = {"ext": Path(caminho).suffix.lower(),
                                 "base64": base64.b64encode(Path(caminho).read_bytes()).decode()}
    return db.para_json(marca)


def _marca_do_perfil(marca_json: str | None, empresa_id: int) -> str | None:
    marca = db.de_json(marca_json) if marca_json else None
    if not marca:
        return marca_json
    arq = marca.pop("logo_arquivo", None)
    marca.pop("logo", None)  # nunca confia em caminho vindo de fora
    if arq and arq.get("ext") in (".png", ".jpg", ".jpeg"):
        dados = base64.b64decode(arq.get("base64") or "", validate=True)
        if 0 < len(dados) <= LOGO_MAX:
            destino = C.dir_dados("marcas") / f"empresa-{empresa_id}{arq['ext']}"
            destino.write_bytes(dados)
            marca["logo"] = str(destino)
    return db.para_json(marca)

CAMPOS_EMPRESA = ["apelido", "cnpj", "razao_social", "nome_fantasia", "inscricao_municipal", "cod_municipio",
                  "municipio", "uf", "logradouro", "numero", "complemento", "bairro", "cep", "telefone", "email",
                  "opcao_simples", "regime_apuracao_simples", "regime_especial", "serie_dps", "marca_json"]
CAMPOS_CLIENTE = ["tipo_doc", "documento", "razao_social", "email", "telefone", "cod_municipio", "municipio", "uf",
                  "cep", "logradouro", "numero", "complemento", "bairro", "ativo"]
CAMPOS_SERVICO = ["nome", "cod_trib_nacional", "cod_trib_municipal", "cod_nbs", "descricao_padrao", "valor_padrao",
                  "cod_local_prestacao", "trib_issqn", "tp_ret_issqn", "cst_pis_cofins", "tp_ret_pis_cofins",
                  "perc_trib_sn", "ativo"]
CAMPOS_MODELO = ["nome", "valor", "valor_minimo", "valor_maximo", "descricao_modelo", "ativo"]


def _so(d: dict, campos: list[str]) -> dict:
    return {k: d.get(k) for k in campos}


def exportar(conn, empresa_id: int) -> dict:
    emp = db.obter(conn, "empresas", empresa_id)
    if not emp:
        raise LookupError(f"Empresa {empresa_id} não encontrada")
    clientes = db.listar(conn, "clientes", empresa_id=empresa_id)
    servicos = db.listar(conn, "servicos", empresa_id=empresa_id)
    doc_por_id = {c["id"]: c["documento"] for c in clientes}
    nome_por_id = {s["id"]: s["nome"] for s in servicos}
    modelos = []
    for m in db.listar(conn, "modelos", empresa_id=empresa_id):
        item = _so(m, CAMPOS_MODELO)
        item["cliente_documento"] = doc_por_id.get(m["cliente_id"])
        item["servico_nome"] = nome_por_id.get(m["servico_id"])
        modelos.append(item)
    return {
        "perfil_emissor_nf_open": VERSAO_PERFIL,
        "empresa": {**_so(emp, CAMPOS_EMPRESA), "marca_json": _marca_para_perfil(emp.get("marca_json"))},
        "clientes": [_so(c, CAMPOS_CLIENTE) for c in clientes],
        "servicos": [_so(s, CAMPOS_SERVICO) for s in servicos],
        "modelos": modelos,
    }


def importar(conn, perfil: dict, certificado_id: int | None = None) -> int:
    if perfil.get("perfil_emissor_nf_open") != VERSAO_PERFIL:
        raise ValueError("Arquivo não é um perfil do Emissor de NF Open Source (versão 1).")
    emp = perfil["empresa"]
    if conn.execute("select 1 from empresas where cnpj = ?", (emp["cnpj"],)).fetchone():
        raise ValueError(f"Já existe uma empresa com o CNPJ {emp['cnpj']}. Apague ou edite a existente.")
    with db.transacao(conn):
        dados = {k: v for k, v in _so(emp, CAMPOS_EMPRESA).items() if v is not None}
        dados["certificado_id"] = certificado_id
        marca = dados.pop("marca_json", None)
        empresa_id = db.inserir(conn, "empresas", dados)
        if marca:
            db.atualizar(conn, "empresas", empresa_id, {"marca_json": _marca_do_perfil(marca, empresa_id)})
        cli_ids, srv_ids = {}, {}
        for c in perfil.get("clientes", []):
            cli_ids[c["documento"]] = db.inserir(conn, "clientes", {
                **{k: v for k, v in _so(c, CAMPOS_CLIENTE).items() if v is not None}, "empresa_id": empresa_id})
        for s in perfil.get("servicos", []):
            srv_ids[s["nome"]] = db.inserir(conn, "servicos", {
                **{k: v for k, v in _so(s, CAMPOS_SERVICO).items() if v is not None}, "empresa_id": empresa_id})
        for m in perfil.get("modelos", []):
            if m.get("cliente_documento") not in cli_ids or m.get("servico_nome") not in srv_ids:
                raise ValueError(f"Modelo '{m.get('nome')}' aponta para cliente ou serviço que não está no perfil.")
            db.inserir(conn, "modelos", {
                **{k: v for k, v in _so(m, CAMPOS_MODELO).items() if v is not None}, "empresa_id": empresa_id,
                "cliente_id": cli_ids[m["cliente_documento"]], "servico_id": srv_ids[m["servico_nome"]]})
    return empresa_id
