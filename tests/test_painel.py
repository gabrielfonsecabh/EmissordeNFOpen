"""Painel: páginas, segurança (CSRF e Host) e o fluxo completo de cadastro até a nota de teste."""

from __future__ import annotations

import io
import re

import pytest

from emissor_nf import config as C
from emissor_nf import db
from emissor_nf.painel.app import criar_app

from .conftest import CNPJ_CLIENTE, CNPJ_EMPRESA, SefinFalsa, gerar_pfx


@pytest.fixture
def cliente_web(ambiente):
    app = criar_app(sefin_factory=SefinFalsa())
    app.testing = True
    with app.test_client() as c:
        c.get("/")
        yield app, c


def _csrf(c, url="/"):
    html = c.get(url).get_data(as_text=True)
    m = re.search(r'name="csrf" value="([0-9a-f]+)"', html)
    return m.group(1) if m else None


@pytest.mark.parametrize("url", ["/", "/certificados", "/empresas", "/emitir", "/notas", "/empresas/nova", "/exemplo.pdf"])
def test_paginas_abrem(cliente_web, url):
    _, c = cliente_web
    r = c.get(url)
    assert r.status_code == 200
    if url.endswith(".pdf"):
        assert r.data[:4] == b"%PDF"
    else:
        assert "TechZyon" in r.get_data(as_text=True)


def test_post_sem_csrf_e_recusado(cliente_web):
    _, c = cliente_web
    assert c.post("/empresas/nova", data={"apelido": "x"}).status_code == 400


def test_host_externo_e_recusado(cliente_web):
    app, c = cliente_web
    app.testing = False
    try:
        assert c.get("/", headers={"Host": "ataque.exemplo.com"}).status_code == 403
        assert c.get("/", headers={"Host": "127.0.0.1:8765"}).status_code == 200
    finally:
        app.testing = True


def test_fluxo_completo_ate_a_nota_de_teste(cliente_web):
    app, c = cliente_web
    t = _csrf(c, "/certificados")
    r = c.post("/certificados", data={"csrf": t, "senha": "segredo", "apelido": "Meu cert",
                                      "arquivo": (io.BytesIO(gerar_pfx()), "cert.pfx")},
               content_type="multipart/form-data", follow_redirects=True)
    assert "cadastrado" in r.get_data(as_text=True)

    t = _csrf(c, "/empresas/nova")
    r = c.post("/empresas/nova", data={
        "csrf": t, "apelido": "Exemplo", "cnpj": "11.222.333/0001-81", "razao_social": "EMPRESA EXEMPLO LTDA",
        "cep": "01001-000", "logradouro": "RUA DO EXEMPLO", "numero": "100", "bairro": "CENTRO",
        "municipio": "São Paulo", "uf": "SP", "cod_municipio": "3550308", "opcao_simples": "3",
        "regime_apuracao_simples": "1", "regime_especial": "0", "serie_dps": "1", "certificado_id": "1"},
        follow_redirects=True)
    assert "Empresa cadastrada" in r.get_data(as_text=True)

    t = _csrf(c, "/empresas/1/clientes/novo")
    r = c.post("/empresas/1/clientes/novo", data={
        "csrf": t, "documento": "33.444.555/0001-81", "razao_social": "CLIENTE FICTICIO", "cep": "13010000",
        "logradouro": "AV MODELO", "numero": "2000", "bairro": "CENTRO", "cod_municipio": "3509502"},
        follow_redirects=True)
    assert "Cliente salvo" in r.get_data(as_text=True)

    t = _csrf(c, "/empresas/1/servicos/novo")
    c.post("/empresas/1/servicos/novo", data={"csrf": t, "nome": "Consultoria", "cod_trib_nacional": "17.02.02",
                                              "perc_trib_sn": "6,00", "trib_issqn": "1", "tp_ret_pis_cofins": "0"})
    t = _csrf(c, "/empresas/1/modelos/novo")
    c.post("/empresas/1/modelos/novo", data={"csrf": t, "nome": "Mensal", "cliente_id": "1", "servico_id": "1",
                                             "valor": "1.500,00", "descricao_modelo": "Consultoria de {mes_ref}/{ano_ref}"})
    conn = db.conectar()
    assert db.obter(conn, "modelos", 1)["valor"] == "1500.00"

    form = {"csrf": _csrf(c, "/emitir"), "empresa_id": "1", "modelo_id": "1", "cliente_id": "1", "servico_id": "1",
            "valor": "", "descricao": "", "mes_referencia": "2026-10", "data_pagamento": "2026-11-05",
            "competencia": "", "certificado_id": "", "ambiente": C.HOMOLOGACAO}
    r = c.post("/emitir/previa", data=form)
    html = r.get_data(as_text=True)
    assert "Consultoria de Outubro/2026" in html and "Emitir nota de teste" in html

    r = c.post("/emitir/confirmar", data=form, follow_redirects=True)
    html = r.get_data(as_text=True)
    assert "NFS-e nº 1" in html and "Abrir PDF" in html
    assert c.get("/notas/1/pdf").data[:4] == b"%PDF"

    # Produção exige digitar EMITIR
    form_prod = {**form, "ambiente": C.PRODUCAO, "csrf": _csrf(c, "/emitir")}
    r = c.post("/emitir/confirmar", data=form_prod, follow_redirects=True)
    assert "digite EMITIR" in r.get_data(as_text=True)
    assert conn.execute("select count(*) from emissoes").fetchone()[0] == 1


def test_validacao_mostra_erros(cliente_web):
    _, c = cliente_web
    t = _csrf(c, "/empresas/nova")
    html = c.post("/empresas/nova", data={"csrf": t, "cnpj": "11.222.333/0001-82", "cep": "123"}).get_data(as_text=True)
    assert "CNPJ inválido" in html and "CEP precisa de 8" in html


def test_documentos_do_cadastro():
    assert CNPJ_EMPRESA != CNPJ_CLIENTE
