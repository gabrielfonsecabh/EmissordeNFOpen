"""Fluxo de emissão com a Sefin simulada: travas, numeração, retomada e arquivos."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from emissor_nf import assinatura as A
from emissor_nf import certificados as CERT
from emissor_nf import config as C
from emissor_nf import db, emissao, perfis
from emissor_nf.sefin import SefinErro

from .conftest import CNPJ_OUTRO, SefinFalsa, gerar_pfx


def _pedido(cad, **kw):
    base = dict(empresa_id=cad["empresa"], cliente_id=cad["cliente"], servico_id=cad["servico"],
                modelo_id=cad["modelo"], ambiente=C.PRODUCAO, mes_referencia="2026-10",
                data_pagamento=dt.date(2026, 11, 5))
    base.update(kw)
    return emissao.Pedido(**base)


def test_previa_monta_descricao_e_numero(conn, cadastro):
    prev = emissao.preparar(conn, _pedido(cadastro))
    assert prev.pode_emitir, prev.bloqueios
    assert prev.descricao == "Serviços administrativos de Outubro/2026, pagamento em 05/11/2026"
    assert str(prev.valor) == "2500.00" and prev.n_dps_previsto == 1


def test_emite_salva_arquivos_e_numera(conn, cadastro):
    sefin = SefinFalsa()
    e = emissao.emitir(conn, _pedido(cadastro), sefin_factory=sefin)
    assert e["status"] == "emitida" and e["numero_nfse"] == "1"
    assert Path(e["xml_path"]).exists() and Path(e["pdf_path"]).exists()
    assert "11222333000181" in e["xml_path"]  # pasta por CNPJ
    A.verificar(sefin.enviadas[0], CERT.carregar(conn, cadastro["cert"]).cert_pem())  # foi assinada de verdade
    e2 = emissao.emitir(conn, _pedido(cadastro, mes_referencia="2026-11"), sefin_factory=sefin)
    assert (e["n_dps"], e2["n_dps"]) == (1, 2)


def test_bloqueia_mesmo_cliente_no_mesmo_mes(conn, cadastro):
    sefin = SefinFalsa()
    emissao.emitir(conn, _pedido(cadastro), sefin_factory=sefin)
    with pytest.raises(emissao.EmissaoErro, match="Já existe nota"):
        emissao.emitir(conn, _pedido(cadastro), sefin_factory=sefin)
    e = emissao.emitir(conn, _pedido(cadastro), sefin_factory=sefin, permitir_repetida=True)
    assert e["status"] == "emitida" and len(sefin.enviadas) == 2


def test_bloqueia_valor_fora_da_faixa(conn, cadastro):
    prev = emissao.preparar(conn, _pedido(cadastro, valor="25.000,00"))
    assert not prev.pode_emitir and "valor" in prev.liberaveis
    assert emissao.preparar(conn, _pedido(cadastro, valor="25.000,00"), forcar_valor=True).pode_emitir


def test_bloqueia_certificado_de_outra_empresa(conn, cadastro):
    outro = CERT.importar(conn, gerar_pfx(CNPJ_OUTRO), "segredo")
    prev = emissao.preparar(conn, _pedido(cadastro, certificado_id=outro["id"]))
    assert any("certificado" in b for b in prev.bloqueios)


def test_bloqueia_certificado_vencido(conn, cadastro):
    db.atualizar(conn, "certificados", cadastro["cert"], {"valido_ate": "2020-01-01"})
    assert any("venceu" in b for b in emissao.preparar(conn, _pedido(cadastro)).bloqueios)


def test_timeout_vira_verificar_e_retomada_nao_reenvia(conn, cadastro):
    sefin = SefinFalsa(erro=SefinErro("A Sefin não respondeu a tempo", ambiguo=True))
    sefin.gerar_mesmo_com_erro = True  # a nota foi gerada, mas a resposta se perdeu
    e = emissao.emitir(conn, _pedido(cadastro), sefin_factory=sefin)
    assert e["status"] == "emitida"  # conferência imediata achou a nota
    assert len(sefin.enviadas) == 1


def test_sefin_fora_do_ar_fica_para_conferir(conn, cadastro):
    sefin = SefinFalsa(erro=SefinErro("Sem conexão com a Sefin"))
    e = emissao.emitir(conn, _pedido(cadastro), sefin_factory=sefin)
    assert e["status"] == "verificar"
    assert [x["id"] for x in emissao.pendentes(conn)] == [e["id"]]
    e2 = emissao.verificar(conn, e["id"], sefin_factory=sefin)  # Sefin voltou
    assert e2["status"] == "emitida" and e2["n_dps"] == e["n_dps"]


def test_rejeicao_da_sefin(conn, cadastro):
    sefin = SefinFalsa(erro=SefinErro("A Sefin recusou a DPS", ["[E0312] código não administrado"], 400))
    e = emissao.emitir(conn, _pedido(cadastro), sefin_factory=sefin)
    assert e["status"] == "rejeitada" and "E0312" in e["mensagens_json"]


def test_numeracao_nao_volta_para_numero_usado(conn, cadastro):
    emissao.emitir(conn, _pedido(cadastro), sefin_factory=SefinFalsa())
    with pytest.raises(ValueError, match="já foi usado"):
        emissao.definir_proximo_numero(conn, cadastro["empresa"], C.PRODUCAO, 1, 1)
    emissao.definir_proximo_numero(conn, cadastro["empresa"], C.PRODUCAO, 1, 50)
    assert emissao.proximo_numero(conn, cadastro["empresa"], C.PRODUCAO, 1) == 50


def test_conflito_de_numeracao(conn, cadastro):
    """Banco local perdido (ou outra máquina): o número já virou outra nota na Sefin. Não pode reenviar."""
    sefin = SefinFalsa()
    emissao.emitir(conn, _pedido(cadastro), sefin_factory=sefin)
    conn.execute("delete from emissoes")
    conn.execute("delete from numeracao")
    e = emissao.emitir(conn, _pedido(cadastro, mes_referencia="2026-11", valor="2600"), sefin_factory=sefin)
    assert e["status"] == "rejeitada" and "conflito" in e["mensagens_json"]
    assert len(sefin.enviadas) == 1


def test_homologacao_vai_para_pasta_de_teste(conn, cadastro):
    e = emissao.emitir(conn, _pedido(cadastro, ambiente=C.HOMOLOGACAO), sefin_factory=SefinFalsa())
    assert "homologacao" in e["xml_path"] and Path(e["pdf_path"]).name.startswith("HOMOLOGACAO_")


def test_pasta_de_saida_da_empresa(conn, cadastro, tmp_path):
    db.atualizar(conn, "empresas", cadastro["empresa"], {"pasta_saida": str(tmp_path / "contador" / "clienteA")})
    e = emissao.emitir(conn, _pedido(cadastro), sefin_factory=SefinFalsa())
    assert str(tmp_path / "contador" / "clienteA") in e["xml_path"]


def test_certificado_senha_errada(conn):
    with pytest.raises(CERT.CertificadoErro, match="Senha"):
        CERT.importar(conn, gerar_pfx(), "errada")


def test_certificado_le_cnpj_alfanumerico(conn):
    from emissor_nf.documentos import gerar_cnpj_ficticio
    cnpj = gerar_cnpj_ficticio("12ABC3450001")
    assert CERT.importar(conn, gerar_pfx(cnpj), "segredo")["documento"] == cnpj


def test_perfil_ida_e_volta(conn, cadastro, ambiente):
    perfil = perfis.exportar(conn, cadastro["empresa"])
    assert "certificado_id" not in perfil["empresa"]
    novo = db.conectar(ambiente / "outro.db")
    eid = perfis.importar(novo, perfil)
    assert len(db.listar(novo, "clientes", empresa_id=eid)) == 1
    assert db.listar(novo, "modelos", empresa_id=eid)[0]["nome"] == "Mensal"
    with pytest.raises(ValueError, match="Já existe"):
        perfis.importar(novo, perfil)


def test_perfil_leva_o_logo_e_nao_leva_caminho(conn, cadastro, ambiente):
    import json as _json
    logo = ambiente / "logo.png"
    logo.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    db.atualizar(conn, "empresas", cadastro["empresa"], {"marca_json": _json.dumps({"nome": "Cliente A", "logo": str(logo)})})
    perfil = perfis.exportar(conn, cadastro["empresa"])
    marca = _json.loads(perfil["empresa"]["marca_json"])
    assert "logo" not in marca and marca["logo_arquivo"]["ext"] == ".png"
    novo = db.conectar(ambiente / "outro.db")
    eid = perfis.importar(novo, perfil)
    nova = _json.loads(db.obter(novo, "empresas", eid)["marca_json"])
    assert Path(nova["logo"]).read_bytes() == logo.read_bytes() and nova["nome"] == "Cliente A"


def test_mesmo_certificado_reaproveita_cadastro(conn):
    pfx = gerar_pfx()
    a = CERT.importar(conn, pfx, "segredo", "Primeiro")
    b = CERT.importar(conn, pfx, "segredo")
    assert a["id"] == b["id"] and b["ja_existia"] and b["apelido"] == "Primeiro"
    assert len(db.listar(conn, "certificados")) == 1


def test_pasta_de_dados_movida_continua_achando_arquivos(conn, cadastro, ambiente, monkeypatch):
    import shutil
    e = emissao.emitir(conn, _pedido(cadastro), sefin_factory=SefinFalsa())
    conn.close()
    shutil.move(str(ambiente / "dados"), str(ambiente / "outro_lugar" / "dados"))
    monkeypatch.setattr(C, "DIR_DADOS", ambiente / "outro_lugar" / "dados")
    novo = db.conectar(ambiente / "outro_lugar" / "dados" / "emissor.db")
    assert C.resolver(e["pdf_path"]).exists()
    assert CERT.carregar(novo, cadastro["cert"]).documento == "11222333000181"
