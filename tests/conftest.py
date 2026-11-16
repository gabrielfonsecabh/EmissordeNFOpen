"""Ambiente de teste isolado: pasta de dados temporária, cofre de senhas em memória e Sefin simulada."""

from __future__ import annotations

import datetime as dt

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from lxml import etree

from emissor_nf import certificados as CERT
from emissor_nf import config as C
from emissor_nf import db, dps
from emissor_nf.exemplo import nfse_ficticia
from emissor_nf.sefin import NotaGerada, SefinErro

CNPJ_EMPRESA = "11222333000181"
CNPJ_CLIENTE = "33444555000181"
CNPJ_OUTRO = "55666777000181"


def gerar_pfx(documento: str = CNPJ_EMPRESA, senha: str = "segredo", dias: int = 365) -> bytes:
    chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f"EMPRESA TESTE:{documento}")])
    agora = dt.datetime.now(dt.timezone.utc)
    # e-CNPJ: o CNPJ vai no SubjectAltName, OID 2.16.76.1.3.3
    san = x509.SubjectAlternativeName([x509.OtherName(x509.ObjectIdentifier("2.16.76.1.3.3"),
                                                      b"\x04\x0e" + documento.encode())])
    cert = (x509.CertificateBuilder().subject_name(nome).issuer_name(nome).public_key(chave.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(agora - dt.timedelta(days=1))
            .not_valid_after(agora + dt.timedelta(days=dias)).add_extension(san, critical=False)
            .sign(chave, hashes.SHA256()))
    return pkcs12.serialize_key_and_certificates(b"teste", chave, cert, None,
                                                 serialization.BestAvailableEncryption(senha.encode()))


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "DIR_DADOS", tmp_path / "dados")
    monkeypatch.setattr(C, "ARQ_BANCO", tmp_path / "dados" / "emissor.db")
    cofre: dict[int, str] = {}
    monkeypatch.setattr(CERT, "guardar_senha", lambda cid, s: cofre.__setitem__(cid, s) or True)
    monkeypatch.setattr(CERT, "ler_senha", lambda cid: cofre.get(cid))
    monkeypatch.setattr(CERT, "apagar_senha", lambda cid: cofre.pop(cid, None))
    return tmp_path


@pytest.fixture
def conn(ambiente):
    c = db.conectar()
    yield c
    c.close()


@pytest.fixture
def cadastro(conn):
    """Certificado, empresa, cliente, serviço e modelo fictícios. Devolve os ids."""
    cert = CERT.importar(conn, gerar_pfx(), "segredo", "Cert teste")
    eid = db.inserir(conn, "empresas", {
        "apelido": "Exemplo", "cnpj": CNPJ_EMPRESA, "razao_social": "EMPRESA EXEMPLO SERVICOS LTDA",
        "inscricao_municipal": "1234567", "cod_municipio": "3550308", "municipio": "São Paulo", "uf": "SP",
        "logradouro": "RUA DO EXEMPLO", "numero": "100", "bairro": "CENTRO", "cep": "01001000",
        "opcao_simples": "3", "regime_apuracao_simples": "1", "regime_especial": "0", "serie_dps": 1,
        "certificado_id": cert["id"]})
    cid = db.inserir(conn, "clientes", {
        "empresa_id": eid, "tipo_doc": "CNPJ", "documento": CNPJ_CLIENTE, "razao_social": "CLIENTE FICTICIO COMERCIO LTDA",
        "email": "financeiro@cliente-exemplo.com.br", "telefone": "1130000000", "cod_municipio": "3509502",
        "municipio": "Campinas", "uf": "SP", "cep": "13010000", "logradouro": "AVENIDA MODELO", "numero": "2000",
        "bairro": "CENTRO"})
    sid = db.inserir(conn, "servicos", {
        "empresa_id": eid, "nome": "Apoio administrativo", "cod_trib_nacional": "170202", "cod_trib_municipal": "004",
        "cod_nbs": "118064000", "cod_local_prestacao": "3509502", "cst_pis_cofins": "07", "tp_ret_pis_cofins": "0",
        "perc_trib_sn": "6.50", "descricao_padrao": "Serviços de {mes_ref}/{ano_ref}"})
    mid = db.inserir(conn, "modelos", {
        "empresa_id": eid, "nome": "Mensal", "cliente_id": cid, "servico_id": sid, "valor": "2500.00",
        "valor_minimo": "2000.00", "valor_maximo": "3000.00",
        "descricao_modelo": "Serviços administrativos de {mes_ref}/{ano_ref}, pagamento em {data_pagamento}"})
    return {"cert": cert["id"], "empresa": eid, "cliente": cid, "servico": sid, "modelo": mid}


class SefinFalsa:
    """Imita a Sefin: guarda as notas por id da DPS e devolve uma NFS-e no formato oficial."""

    def __init__(self, erro: SefinErro | None = None, erro_vezes: int = 1):
        self.notas: dict[str, NotaGerada] = {}
        self.enviadas: list[bytes] = []
        self.erro, self.erro_vezes = erro, erro_vezes
        self.gerar_mesmo_com_erro = False

    def __call__(self, ambiente, cert):
        return self

    def chave_da_dps(self, id_dps):
        nota = self.notas.get(id_dps)
        return nota.chave if nota else None

    def baixar_nfse(self, chave):
        return next(n for n in self.notas.values() if n.chave == chave)

    def emitir(self, dps_bytes):
        self.enviadas.append(dps_bytes)
        el = etree.fromstring(dps_bytes)
        id_dps = el.find(f"{{{dps.NS}}}infDPS").get("Id")
        if self.erro and self.erro_vezes > 0:
            self.erro_vezes -= 1
            if self.gerar_mesmo_com_erro:
                self._gerar(el, id_dps)
            raise self.erro
        return self._gerar(el, id_dps)

    def _gerar(self, el, id_dps):
        numero = str(len(self.notas) + 1)
        empresa = {"razao_social": "EMPRESA EXEMPLO SERVICOS LTDA", "inscricao_municipal": "1234567",
                   "logradouro": "RUA DO EXEMPLO", "numero": "100", "bairro": "CENTRO", "cod_municipio": "3550308",
                   "uf": "SP", "cep": "01001000"}
        xml = nfse_ficticia(el, numero, "São Paulo", "Campinas", "Apoio administrativo.", empresa)
        chave = etree.fromstring(xml).find(f"{{{dps.NS}}}infNFSe").get("Id")[3:]
        nota = NotaGerada(chave, xml)
        self.notas[id_dps] = nota
        return nota
