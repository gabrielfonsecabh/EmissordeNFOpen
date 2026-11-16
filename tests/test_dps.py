"""DPS: estrutura idêntica à de uma nota real aceita pela Sefin, esquemas oficiais e regras de bloqueio."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree

from emissor_nf import config as C
from emissor_nf import documentos, dps

REF = Path(__file__).parent / "referencia" / "nfse_referencia_anonimizada.xml"
NS = {"n": dps.NS}

EMPRESA = {"cnpj": "11222333000181", "inscricao_municipal": "1234567", "cod_municipio": "3550308",
           "opcao_simples": "3", "regime_apuracao_simples": "1", "regime_especial": "0"}
CLIENTE = {"tipo_doc": "CNPJ", "documento": "33444555000181", "razao_social": "CLIENTE FICTICIO COMERCIO LTDA",
           "cod_municipio": "3509502", "cep": "13010000", "logradouro": "AVENIDA MODELO", "numero": "2000",
           "bairro": "CENTRO", "telefone": "1130000000", "email": "financeiro@cliente-exemplo.com.br"}
SERVICO = {"cod_trib_nacional": "170202", "cod_trib_municipal": "004", "cod_nbs": "118064000",
           "cod_local_prestacao": "3509502", "trib_issqn": "1", "tp_ret_issqn": "1", "cst_pis_cofins": "07",
           "tp_ret_pis_cofins": "0", "perc_trib_sn": "6.50"}


def _c14n(el) -> bytes:
    return etree.tostring(etree.fromstring(etree.tostring(el)), method="c14n")


def _dados(**kw):
    base = dict(tp_amb="1", dh_emi=dt.datetime(2026, 10, 5, 10, 0, 0, tzinfo=C.TZ), serie=70000, n_dps=11,
                d_compet=dt.date(2026, 10, 1), descricao="Prestação de serviços administrativos referentes a Setembro/2026.",
                valor=Decimal("2500.00"), ver_aplic="EmissorWeb_1.6.0.0")
    base.update(kw)
    return dps.DadosNota(**base)


def test_dps_identica_a_nota_real_aceita_pela_sefin():
    gerada = dps.montar(EMPRESA, CLIENTE, SERVICO, _dados(), permitir_serie_emissor_web=True, forcar_leiaute="v1_01")
    real = etree.parse(str(REF)).getroot().find("n:infNFSe/n:DPS", NS)
    assert _c14n(gerada) == _c14n(real)


@pytest.mark.parametrize("lei", ["v1_01", "v1_01_nt009"])
def test_passa_nos_esquemas_oficiais(lei):
    dps.validar(dps.montar(EMPRESA, CLIENTE, SERVICO, _dados(serie=1, n_dps=1), forcar_leiaute=lei), lei)


def test_leiaute_por_data_e_ambiente():
    assert dps.leiaute("1", dt.datetime(2026, 11, 30, 23, tzinfo=C.TZ)) == "v1_01"
    assert dps.leiaute("1", dt.datetime(2026, 12, 1, 0, tzinfo=C.TZ)) == "v1_01_nt009"
    assert dps.leiaute("2", dt.datetime(2026, 11, 1, tzinfo=C.TZ)) == "v1_01_nt009"


def test_nt009_ordem():
    el = dps.montar(EMPRESA, CLIENTE, SERVICO, _dados(serie=1), forcar_leiaute="v1_01_nt009")
    tags = [etree.QName(x).localname for x in el.find("n:infDPS", NS)]
    assert tags.index("finNFSe") == tags.index("tpEmit") + 1
    assert [etree.QName(x).localname for x in el.find("n:infDPS/n:serv/n:cServ", NS)][-1] == "xDescServ"


def test_tomador_cpf_sem_contato_e_mei():
    cli = {**CLIENTE, "tipo_doc": "CPF", "documento": "12345678909", "telefone": None, "email": None, "complemento": "SALA 2"}
    emp = {**EMPRESA, "opcao_simples": "2", "regime_apuracao_simples": None}
    srv = {**SERVICO, "cst_pis_cofins": None, "perc_trib_sn": None}
    el = dps.montar(emp, cli, srv, _dados(serie=1), forcar_leiaute="v1_01_nt009")
    dps.validar(el, "v1_01_nt009")
    assert el.findtext("n:infDPS/n:toma/n:CPF", namespaces=NS) == "12345678909"
    assert el.findtext("n:infDPS/n:valores/n:trib/n:totTrib/n:indTotTrib", namespaces=NS) == "0"
    assert el.find("n:infDPS/n:valores/n:trib/n:tribFed", NS) is None


def test_cnpj_alfanumerico_no_leiaute_novo():
    cnpj = documentos.gerar_cnpj_ficticio("12ABC3450001")
    assert documentos.cnpj_valido(cnpj)
    el = dps.montar({**EMPRESA, "cnpj": cnpj}, CLIENTE, SERVICO, _dados(serie=1), forcar_leiaute="v1_01_nt009")
    dps.validar(el, "v1_01_nt009")
    assert cnpj in el.find("n:infDPS", NS).get("Id")


@pytest.mark.parametrize("mudanca, trecho", [
    ({"serie": 70000}, "Série"),
    ({"serie": 1, "d_compet": dt.date(2026, 10, 9)}, "competência"),
    ({"serie": 1, "valor": Decimal("0")}, "valor"),
    ({"serie": 1, "descricao": "   "}, "descrição"),
])
def test_bloqueios_de_dados(mudanca, trecho):
    with pytest.raises(dps.DpsErro, match=f"(?i){trecho}"):
        dps.montar(EMPRESA, CLIENTE, SERVICO, _dados(**mudanca))


def test_bloqueia_iss_retido_e_simples_sem_percentual():
    with pytest.raises(dps.DpsErro, match="retido"):
        dps.montar(EMPRESA, CLIENTE, {**SERVICO, "tp_ret_issqn": "2"}, _dados(serie=1))
    with pytest.raises(dps.DpsErro, match="percentual"):
        dps.montar(EMPRESA, CLIENTE, {**SERVICO, "perc_trib_sn": None}, _dados(serie=1))


def test_render_descricao():
    txt = dps.render_descricao("Ref {mes_ref}/{ano_ref} ({mes_num}) pago em {data_pagamento}", "2026-11", dt.date(2026, 12, 4))
    assert txt == "Ref Novembro/2026 (11) pago em 04/12/2026"


def test_documentos():
    assert documentos.cnpj_valido("11.222.333/0001-81")
    assert not documentos.cnpj_valido("11.222.333/0001-82")
    assert documentos.cnpj_valido("12.ABC.345/01DE-35")  # exemplo oficial da Receita
    assert documentos.cpf_valido("123.456.789-09")
    assert not documentos.cpf_valido("111.111.111-11")
    assert documentos.formatar_documento("11222333000181") == "11.222.333/0001-81"
