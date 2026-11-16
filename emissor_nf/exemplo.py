"""Nota FICTÍCIA para ver o PDF sem emitir nada nem precisar de certificado.

Monta uma DPS de verdade (mesmo código da emissão) com dados inventados e a embrulha no formato
da NFS-e que a Sefin devolve. O PDF sai com a faixa "MODELO, SEM VALOR FISCAL".
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from lxml import etree

from . import config as C
from . import danfse
from . import dps as D

EMPRESA = {
    "cnpj": "11222333000181", "razao_social": "EMPRESA EXEMPLO SERVICOS LTDA", "inscricao_municipal": "1234567",
    "cod_municipio": "3550308", "municipio": "São Paulo", "uf": "SP", "logradouro": "RUA DO EXEMPLO",
    "numero": "100", "bairro": "CENTRO", "cep": "01001000", "opcao_simples": "3", "regime_apuracao_simples": "1",
    "regime_especial": "0", "serie_dps": 1,
}
CLIENTE = {
    "tipo_doc": "CNPJ", "documento": "33444555000181", "razao_social": "CLIENTE FICTICIO COMERCIO LTDA",
    "email": "financeiro@cliente-exemplo.com.br", "telefone": "1130000000", "cod_municipio": "3509502",
    "cep": "13010000", "logradouro": "AVENIDA MODELO", "numero": "2000", "complemento": "SALA 3", "bairro": "CENTRO",
}
SERVICO = {
    "cod_trib_nacional": "010101", "cod_nbs": None, "cod_local_prestacao": None,
    "trib_issqn": "1", "tp_ret_issqn": "1", "perc_trib_sn": "6.00",
}


def nfse_ficticia(dps_el, numero: str, municipio_emit: str, municipio_prest: str,
                  x_trib_nac: str, empresa: dict) -> bytes:
    ns = D.NS
    raiz = etree.Element(f"{{{ns}}}NFSe", nsmap={None: ns})
    raiz.set("versao", D.VERSAO)
    inf = etree.SubElement(raiz, f"{{{ns}}}infNFSe")
    inf_dps = dps_el.find(f"{{{ns}}}infDPS")
    cnpj = inf_dps.findtext(f"{{{ns}}}prest/{{{ns}}}CNPJ")
    cmun = inf_dps.findtext(f"{{{ns}}}cLocEmi")
    inf.set("Id", f"NFS{cmun}2{cnpj}{'0' * 13}{int(numero):013d}"[:53].ljust(53, "0"))

    def sub(pai, tag, txt=None):
        el = etree.SubElement(pai, f"{{{ns}}}{tag}")
        if txt is not None:
            el.text = txt
        return el

    sub(inf, "xLocEmi", municipio_emit)
    sub(inf, "xLocPrestacao", municipio_prest)
    sub(inf, "nNFSe", numero)
    sub(inf, "xLocIncid", municipio_emit)
    sub(inf, "xTribNac", x_trib_nac)
    sub(inf, "dhProc", inf_dps.findtext(f"{{{ns}}}dhEmi"))
    emit = sub(inf, "emit")
    sub(emit, "CNPJ", cnpj)
    sub(emit, "IM", empresa.get("inscricao_municipal"))
    sub(emit, "xNome", empresa["razao_social"])
    end = sub(emit, "enderNac")
    sub(end, "xLgr", empresa["logradouro"])
    sub(end, "nro", empresa["numero"])
    sub(end, "xBairro", empresa["bairro"])
    sub(end, "cMun", empresa["cod_municipio"])
    sub(end, "UF", empresa["uf"])
    sub(end, "CEP", empresa["cep"])
    val = sub(inf, "valores")
    sub(val, "vLiq", inf_dps.findtext(f"{{{ns}}}valores/{{{ns}}}vServPrest/{{{ns}}}vServ"))
    inf.append(dps_el)
    return etree.tostring(raiz, encoding="utf-8", xml_declaration=True)


def xml_ficticio(empresa: dict | None = None) -> bytes:
    emp = {**EMPRESA, **(empresa or {})}
    dados = D.DadosNota(
        tp_amb=C.HOMOLOGACAO, dh_emi=datetime(2026, 12, 4, 9, 12, 38, tzinfo=C.TZ), serie=1, n_dps=42,
        d_compet=date(2026, 12, 4), valor=Decimal("4800.00"),
        descricao="Desenvolvimento de site institucional responsivo, configuração de domínio e e-mail "
                  "profissional. Referência: proposta 2026-041, entrega em dezembro de 2026.")
    el = D.montar(emp, CLIENTE, SERVICO, dados, forcar_leiaute="v1_01_nt009")
    return nfse_ficticia(el, "42", emp["municipio"], "Campinas",
                         "Análise e desenvolvimento de sistemas.", emp)


def gerar(destino_dir: Path | None = None, marca: dict | None = None) -> Path:
    destino_dir = destino_dir or C.dir_dados("exemplos")
    destino_dir.mkdir(parents=True, exist_ok=True)
    return danfse.gerar(xml_ficticio(), destino_dir / "MODELO_DANFSe.pdf", marca,
                        aviso="MODELO · NOTA FICTÍCIA · SEM VALOR FISCAL")
