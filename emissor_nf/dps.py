"""Montagem e validação da DPS (Declaração de Prestação de Serviço), leiaute 1.01.

A ordem dos elementos segue os XSDs oficiais e foi conferida contra uma DPS real aceita
pela Sefin Nacional (ver tests/referencia/, com os dados trocados por fictícios).

Escopo desta versão (ver a seção "O que ainda não faz" do README):
  * prestador com CNPJ (numérico ou alfanumérico), optante do Simples (ME/EPP) ou MEI
  * tomador nacional com CNPJ ou CPF
  * ISS sem retenção, sem deduções, sem o grupo IBS/CBS
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache

from lxml import etree

from . import config as C
from .documentos import limpar

NS = "http://www.sped.fazenda.gov.br/nfse"
VERSAO = "1.01"


class DpsErro(Exception):
    """Problema nos dados, encontrado antes de qualquer envio."""


@dataclass
class DadosNota:
    tp_amb: str
    dh_emi: datetime
    serie: int
    n_dps: int
    d_compet: date
    descricao: str
    valor: Decimal
    ver_aplic: str = C.VERSAO_APLICATIVO


def leiaute(tp_amb: str, quando: datetime) -> str:
    if tp_amb == C.HOMOLOGACAO or quando >= C.INICIO_NT009_PRODUCAO:
        return "v1_01_nt009"
    return "v1_01"


def id_dps(cod_mun: str, cnpj: str, serie: int, n_dps: int) -> str:
    # DPS + município (7) + tipo de inscrição (2 = CNPJ) + CNPJ (14) + série (5) + número (15)
    return f"DPS{cod_mun}2{limpar(cnpj).zfill(14)}{int(serie):05d}{int(n_dps):015d}"


def _dec(v) -> str:
    return str(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _sub(pai, tag: str, texto: str | None = None):
    el = etree.SubElement(pai, f"{{{NS}}}{tag}")
    if texto is not None:
        el.text = texto
    return el


def _opt(pai, tag: str, texto) -> None:
    if texto not in (None, ""):
        _sub(pai, tag, str(texto))


def montar(prestador: dict, tomador: dict, servico: dict, d: DadosNota,
           *, permitir_serie_emissor_web: bool = False, forcar_leiaute: str | None = None) -> etree._Element:
    """prestador, tomador e servico são linhas das tabelas empresas, clientes e servicos."""
    p, t, s = prestador, tomador, servico

    if not (1 <= int(d.serie) <= 49999) and not permitir_serie_emissor_web:
        raise DpsErro(f"Série {d.serie} fora da faixa de sistema próprio (1 a 49999). A 70000 é do Emissor Web.")
    if int(d.n_dps) < 1:
        raise DpsErro("O número da DPS precisa ser maior que zero.")
    if Decimal(str(d.valor)) <= 0:
        raise DpsErro("O valor do serviço precisa ser maior que zero.")
    if d.d_compet > d.dh_emi.date():
        raise DpsErro("A competência não pode ser depois da data de emissão (a Sefin rejeita com E0015).")
    descricao = " ".join((d.descricao or "").split())
    if not descricao:
        raise DpsErro("A descrição do serviço está vazia.")
    if len(descricao) > 2000:
        raise DpsErro("A descrição passa de 2000 caracteres.")
    if (s.get("tp_ret_issqn") or "1") != "1":
        raise DpsErro("ISS retido pelo tomador ainda não é suportado nesta versão (veja 'O que ainda não faz' no README).")

    nt009 = (forcar_leiaute or leiaute(d.tp_amb, d.dh_emi)) == "v1_01_nt009"
    cnpj_prest = limpar(p["cnpj"])

    dps = etree.Element(f"{{{NS}}}DPS", nsmap={None: NS})
    dps.set("versao", VERSAO)
    inf = _sub(dps, "infDPS")
    inf.set("Id", id_dps(p["cod_municipio"], cnpj_prest, d.serie, d.n_dps))

    _sub(inf, "tpAmb", d.tp_amb)
    _sub(inf, "dhEmi", d.dh_emi.isoformat(timespec="seconds"))
    _sub(inf, "verAplic", d.ver_aplic)
    _sub(inf, "serie", str(int(d.serie)))
    _sub(inf, "nDPS", str(int(d.n_dps)))
    _sub(inf, "dCompet", d.d_compet.isoformat())
    _sub(inf, "tpEmit", "1")
    if nt009:
        _sub(inf, "finNFSe", "0")
    _sub(inf, "cLocEmi", p["cod_municipio"])

    prest = _sub(inf, "prest")
    _sub(prest, "CNPJ", cnpj_prest)
    _opt(prest, "IM", p.get("inscricao_municipal"))
    reg = _sub(prest, "regTrib")
    op = p.get("opcao_simples") or "3"
    _sub(reg, "opSimpNac", op)
    if op == "3":
        _opt(reg, "regApTribSN", p.get("regime_apuracao_simples"))
    _sub(reg, "regEspTrib", p.get("regime_especial") or "0")

    toma = _sub(inf, "toma")
    doc = limpar(t.get("documento"))
    if t.get("tipo_doc") == "CPF" or len(doc) == 11:
        _sub(toma, "CPF", doc)
    elif len(doc) == 14:
        _sub(toma, "CNPJ", doc)
    else:
        raise DpsErro(f"Documento do cliente inválido: {t.get('documento')!r}")
    _sub(toma, "xNome", t["razao_social"])
    end = _sub(toma, "end")
    end_nac = _sub(end, "endNac")
    _sub(end_nac, "cMun", t["cod_municipio"])
    _sub(end_nac, "CEP", limpar(t["cep"]))
    _sub(end, "xLgr", t["logradouro"])
    _sub(end, "nro", t["numero"])
    _opt(end, "xCpl", t.get("complemento"))
    _sub(end, "xBairro", t["bairro"])
    _opt(toma, "fone", limpar(t.get("telefone")) or None)
    _opt(toma, "email", t.get("email"))

    serv = _sub(inf, "serv")
    loc = _sub(serv, "locPrest")
    _sub(loc, "cLocPrestacao", s.get("cod_local_prestacao") or t["cod_municipio"])
    c_serv = _sub(serv, "cServ")
    _sub(c_serv, "cTribNac", s["cod_trib_nacional"])
    _opt(c_serv, "cTribMun", s.get("cod_trib_municipal"))
    if nt009:
        _opt(c_serv, "cNBS", s.get("cod_nbs"))
        _sub(c_serv, "xDescServ", descricao)
    else:
        _sub(c_serv, "xDescServ", descricao)
        _opt(c_serv, "cNBS", s.get("cod_nbs"))

    valores = _sub(inf, "valores")
    v_serv_prest = _sub(valores, "vServPrest")
    _sub(v_serv_prest, "vServ", _dec(d.valor))
    trib = _sub(valores, "trib")
    trib_mun = _sub(trib, "tribMun")
    _sub(trib_mun, "tribISSQN", s.get("trib_issqn") or "1")
    _sub(trib_mun, "tpRetISSQN", "1")
    if s.get("cst_pis_cofins"):
        trib_fed = _sub(trib, "tribFed")
        pc = _sub(trib_fed, "piscofins")
        _sub(pc, "CST", s["cst_pis_cofins"])
        _opt(pc, "tpRetPisCofins", s.get("tp_ret_pis_cofins"))
    tot = _sub(trib, "totTrib")
    if op == "3":
        if s.get("perc_trib_sn") in (None, ""):
            raise DpsErro("Empresa do Simples (ME/EPP) precisa do percentual aproximado de tributos no serviço "
                          "(campo 'Tributos aproximados do Simples, %'). Sem ele a Sefin rejeita (E0712).")
        _sub(tot, "pTotTribSN", _dec(s["perc_trib_sn"]))
    elif op == "2":
        _sub(tot, "indTotTrib", "0")  # MEI: pTotTribSN é proibido
    else:
        raise DpsErro("Empresa não optante do Simples ainda não é suportada nesta versão (veja 'O que ainda não faz' no README).")

    return dps


def para_bytes(el) -> bytes:
    return etree.tostring(el, encoding="utf-8", xml_declaration=True)


@lru_cache(maxsize=4)
def _schema(pasta: str) -> etree.XMLSchema:
    return etree.XMLSchema(etree.parse(str(C.DIR_SCHEMAS / pasta / "DPS_v1.01.xsd")))


def validar(el, pasta_leiaute: str) -> None:
    schema = _schema(pasta_leiaute)
    doc = etree.fromstring(etree.tostring(el))
    if not schema.validate(doc):
        msgs = "; ".join(f"linha {e.line}: {e.message}" for e in schema.error_log)
        raise DpsErro(f"A DPS não passou no esquema oficial ({pasta_leiaute}): {msgs}")


def render_descricao(modelo: str, mes_referencia: str | None, data_pagamento: date | None) -> str:
    """Troca {mes_ref}, {ano_ref}, {mes_num} e {data_pagamento} no texto. mes_referencia = 'AAAA-MM'."""
    mes_nome = ano = mes_num = ""
    if mes_referencia and len(mes_referencia) == 7 and mes_referencia[4] == "-":
        ano, mm = mes_referencia.split("-")
        if mm.isdigit() and 1 <= int(mm) <= 12:
            mes_nome, mes_num = C.MESES[int(mm) - 1], mm
    return (modelo or "").replace("{mes_ref}", mes_nome).replace("{ano_ref}", ano) \
        .replace("{mes_num}", mes_num) \
        .replace("{data_pagamento}", data_pagamento.strftime("%d/%m/%Y") if data_pagamento else "")
