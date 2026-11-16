"""Certificados A1 (.pfx/.p12): importação, leitura e TLS mútuo.

Onde fica cada coisa:
  * o arquivo .pfx é COPIADO para dados/certificados/<id>.pfx (permissão só do seu usuário);
  * a senha vai para o cofre do sistema operacional (Chaves no macOS, Gerenciador de
    Credenciais no Windows, Secret Service no Linux), via biblioteca `keyring`;
  * se o cofre não estiver disponível, a senha pode vir da variável EMISSOR_SENHA_CERT_<id>.
Nada disso sai do seu computador.
"""

from __future__ import annotations

import os
import re
import secrets
import shutil
import ssl
import tempfile
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import certifi
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from . import config as C
from . import db

OID_CNPJ = "2.16.76.1.3.3"
OID_CPF_PF = "2.16.76.1.3.1"  # dados do titular pessoa física (CPF nas posições 9 a 19)


class CertificadoErro(Exception):
    pass


@dataclass
class Certificado:
    chave: object
    cert: x509.Certificate
    cadeia: list

    @classmethod
    def abrir_bytes(cls, dados: bytes, senha: str) -> "Certificado":
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)  # alguns .pfx vêm em BER; a leitura funciona
                chave, cert, extras = pkcs12.load_key_and_certificates(dados, (senha or "").encode())
        except ValueError as exc:
            raise CertificadoErro("Senha incorreta ou arquivo que não é um certificado A1 (.pfx/.p12).") from exc
        if chave is None or cert is None:
            raise CertificadoErro("O arquivo não tem a chave privada junto. Exporte o certificado A1 com a chave.")
        return cls(chave, cert, list(extras or []))

    @classmethod
    def abrir(cls, arquivo: str | Path, senha: str) -> "Certificado":
        caminho = Path(arquivo)
        if not caminho.exists():
            raise CertificadoErro(f"Arquivo do certificado não encontrado: {caminho}")
        return cls.abrir_bytes(caminho.read_bytes(), senha)

    @property
    def titular(self) -> str:
        cn = self.cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        return str(cn[0].value) if cn else self.cert.subject.rfc4514_string()

    @property
    def documento(self) -> str | None:
        """CNPJ do certificado e-CNPJ (inclusive alfanumérico) ou CPF do e-CPF."""
        try:
            san = self.cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
            for nome in san.get_values_for_type(x509.OtherName):
                bruto = re.sub(rb"[^0-9A-Za-z]", b"", nome.value).decode("ascii", "ignore").upper()
                if nome.type_id.dotted_string == OID_CNPJ and len(bruto) >= 14:
                    return bruto[-14:]
                if nome.type_id.dotted_string == OID_CPF_PF and len(bruto) >= 19:
                    return bruto[8:19]
        except x509.ExtensionNotFound:
            pass
        m = re.search(r"([0-9A-Z]{12}\d{2})$", self.titular)
        return m.group(1) if m else None

    @property
    def valido_ate(self) -> datetime:
        return self.cert.not_valid_after_utc

    @property
    def dias_para_vencer(self) -> int:
        return (self.valido_ate - datetime.now(timezone.utc)).days

    def cert_pem(self) -> bytes:
        return self.cert.public_bytes(serialization.Encoding.PEM)

    def ssl_context(self) -> ssl.SSLContext:
        """TLS com o certificado do cliente. O ssl do Python só lê chave de arquivo: ela é gravada
        cifrada com uma senha aleatória num temporário e apagada logo em seguida."""
        ctx = ssl.create_default_context(cafile=certifi.where())
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        senha_tmp = secrets.token_hex(16).encode()
        pasta = tempfile.mkdtemp(prefix="emissor-")
        cert_path = os.path.join(pasta, "c.pem")
        key_path = os.path.join(pasta, "k.pem")
        try:
            with open(cert_path, "wb") as fh:
                fh.write(self.cert_pem())
                for extra in self.cadeia:
                    fh.write(extra.public_bytes(serialization.Encoding.PEM))
            fd = os.open(key_path, os.O_WRONLY | os.O_CREAT, 0o600)
            with os.fdopen(fd, "wb") as fh:
                fh.write(self.chave.private_bytes(
                    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                    serialization.BestAvailableEncryption(senha_tmp)))
            ctx.load_cert_chain(cert_path, key_path, password=senha_tmp)
        finally:
            for f in (cert_path, key_path):
                try:
                    os.remove(f)
                except OSError:
                    pass
            os.rmdir(pasta)
        return ctx


# --- senha no cofre do sistema ----------------------------------------------------------------

def _conta(cert_id: int) -> str:
    return f"certificado-{cert_id}"


def guardar_senha(cert_id: int, senha: str) -> bool:
    """Devolve True se gravou no cofre; False se o cofre não está disponível neste computador."""
    try:
        import keyring
        keyring.set_password(C.KEYRING_SERVICO, _conta(cert_id), senha)
        return True
    except Exception:  # noqa: BLE001 (keyring levanta tipos diferentes por sistema)
        return False


def ler_senha(cert_id: int) -> str | None:
    env = os.environ.get(f"EMISSOR_SENHA_CERT_{cert_id}")
    if env:
        return env
    try:
        import keyring
        return keyring.get_password(C.KEYRING_SERVICO, _conta(cert_id))
    except Exception:  # noqa: BLE001
        return None


def apagar_senha(cert_id: int) -> None:
    try:
        import keyring
        keyring.delete_password(C.KEYRING_SERVICO, _conta(cert_id))
    except Exception:  # noqa: BLE001
        pass


# --- cadastro ---------------------------------------------------------------------------------

def importar(conn, dados_pfx: bytes, senha: str, apelido: str | None = None) -> dict:
    """Confere a senha, copia o .pfx para dados/certificados e guarda a senha no cofre."""
    cert = Certificado.abrir_bytes(dados_pfx, senha)
    impressao = cert.cert.fingerprint(hashes.SHA256()).hex()
    with db.transacao(conn):
        existente = conn.execute("select id from certificados where impressao = ?", (impressao,)).fetchone()
        if existente:  # o mesmo certificado de novo: atualiza arquivo e senha, mantém o id (empresas ligadas a ele)
            cert_id = existente["id"]
            if apelido:
                db.atualizar(conn, "certificados", cert_id, {"apelido": apelido[:120]})
        else:
            cert_id = db.inserir(conn, "certificados", {
                "apelido": (apelido or cert.titular)[:120], "arquivo": "", "documento": cert.documento,
                "titular": cert.titular, "valido_ate": cert.valido_ate.date().isoformat(), "impressao": impressao})
        destino = C.dir_dados("certificados") / f"{cert_id}.pfx"
        fd = os.open(destino, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(dados_pfx)
        db.atualizar(conn, "certificados", cert_id, {"arquivo": str(destino)})
    no_cofre = guardar_senha(cert_id, senha)
    reg = db.obter(conn, "certificados", cert_id)
    reg["senha_no_cofre"] = no_cofre
    reg["ja_existia"] = bool(existente)
    return reg


def carregar(conn, cert_id: int, senha: str | None = None) -> Certificado:
    reg = db.obter(conn, "certificados", cert_id)
    if not reg:
        raise CertificadoErro(f"Certificado {cert_id} não cadastrado.")
    senha = senha if senha is not None else ler_senha(cert_id)
    if senha is None:
        raise CertificadoErro(
            f"A senha do certificado '{reg['apelido']}' não está no cofre do sistema. Cadastre de novo o "
            f"certificado ou defina a variável EMISSOR_SENHA_CERT_{cert_id}.")
    return Certificado.abrir(C.resolver(reg["arquivo"]), senha)


def remover(conn, cert_id: int) -> None:
    reg = db.obter(conn, "certificados", cert_id)
    if not reg:
        return
    apagar_senha(cert_id)
    try:
        Path(reg["arquivo"]).unlink(missing_ok=True)
    except OSError:
        pass
    conn.execute("delete from certificados where id = ?", (cert_id,))


def copiar_arquivo_seguro(origem: Path, destino: Path) -> None:
    shutil.copyfile(origem, destino)
    os.chmod(destino, 0o600)
