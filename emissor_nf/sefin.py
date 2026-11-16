"""Cliente REST da Sefin Nacional (TLS mútuo com o certificado A1).

Toda chamada fica registrada em dados/logs/ (resposta da Sefin, com o XML decodificado),
para qualquer rejeição poder ser investigada depois. Os logs ficam só no seu computador.
"""

from __future__ import annotations

import base64
import gzip
import json
from dataclasses import dataclass, field
from typing import Any

import requests
from requests.adapters import HTTPAdapter

from . import config as C
from .certificados import Certificado


class SefinErro(Exception):
    def __init__(self, resumo: str, mensagens: list[str] | None = None, status: int | None = None, ambiguo: bool = False):
        self.resumo = resumo
        self.mensagens = mensagens or []
        self.status = status
        self.ambiguo = ambiguo  # pode ter sido processado (timeout depois do envio)
        detalhes = " | ".join(self.mensagens)
        super().__init__(f"{resumo}: {detalhes}" if detalhes else resumo)


@dataclass
class NotaGerada:
    chave: str
    xml: bytes
    alertas: list[str] = field(default_factory=list)
    bruto: dict = field(default_factory=dict)


def gzip_b64(dados: bytes) -> str:
    return base64.b64encode(gzip.compress(dados)).decode("ascii")


def ungzip_b64(texto: str) -> bytes:
    return gzip.decompress(base64.b64decode(texto))


def _get(d: Any, chave: str) -> Any:
    """Busca chave ignorando maiúsculas/minúsculas (a API varia)."""
    if not isinstance(d, dict):
        return None
    alvo = chave.lower()
    for k, v in d.items():
        if k.lower() == alvo:
            return v
    return None


def _mensagens(dados: Any, *nomes: str) -> list[str]:
    out: list[str] = []
    for nome in nomes:
        itens = _get(dados, nome)
        if isinstance(itens, dict):
            itens = [itens]
        for it in itens or []:
            if isinstance(it, dict):
                cod = _get(it, "codigo") or ""
                desc = _get(it, "descricao") or _get(it, "mensagem") or json.dumps(it, ensure_ascii=False)
                comp = _get(it, "complemento")
                out.append(f"[{cod}] {desc}" + (f" ({comp})" if comp else ""))
            else:
                out.append(str(it))
    return out


class _AdapterTLS(HTTPAdapter):
    def __init__(self, ctx, **kw):
        self._ctx = ctx
        super().__init__(**kw)

    def init_poolmanager(self, *a, **kw):
        kw["ssl_context"] = self._ctx
        return super().init_poolmanager(*a, **kw)

    def proxy_manager_for(self, *a, **kw):
        kw["ssl_context"] = self._ctx
        return super().proxy_manager_for(*a, **kw)


class Sefin:
    def __init__(self, tp_amb: str, cert: Certificado, ver_aplic: str = C.VERSAO_APLICATIVO):
        self.tp_amb = tp_amb
        self.base = C.URL_SEFIN[tp_amb]
        self.http = requests.Session()
        self.http.mount("https://", _AdapterTLS(cert.ssl_context()))
        self.http.headers.update({"Accept": "application/json", "User-Agent": ver_aplic})

    # --- log -----------------------------------------------------------------
    def _log(self, op: str, conteudo: dict) -> None:
        nome = f"{C.agora().strftime('%Y%m%d-%H%M%S')}_{'prod' if self.tp_amb == C.PRODUCAO else 'homol'}_{op}.json"
        (C.dir_dados("logs") / nome).write_text(json.dumps(conteudo, ensure_ascii=False, indent=2), encoding="utf-8")

    def _req(self, metodo: str, url: str, op: str, **kw) -> tuple[int, Any]:
        try:
            r = self.http.request(metodo, url, timeout=(15, 90), **kw)
        except requests.exceptions.ReadTimeout as exc:
            self._log(op, {"url": url, "erro": "timeout de leitura"})
            raise SefinErro("A Sefin não respondeu a tempo; a nota PODE ter sido gerada", ambiguo=True) from exc
        except requests.exceptions.SSLError as exc:
            self._log(op, {"url": url, "erro": str(exc)})
            raise SefinErro("Falha no TLS com o certificado (certificado recusado ou vencido?)", [str(exc)]) from exc
        except requests.exceptions.ConnectionError as exc:
            self._log(op, {"url": url, "erro": str(exc)})
            raise SefinErro("Sem conexão com a Sefin", [str(exc)]) from exc
        try:
            dados = r.json()
        except ValueError:
            dados = {"texto": r.text[:4000]}
        self._log(op, {"url": url, "status": r.status_code, "resposta": _sem_xml(dados)})
        return r.status_code, dados

    # --- operações -------------------------------------------------------------
    def emitir(self, dps_assinada: bytes) -> NotaGerada:
        status, dados = self._req("POST", f"{self.base}/nfse", "emitir", json={"dpsXmlGZipB64": gzip_b64(dps_assinada)})
        chave = _get(dados, "chaveAcesso")
        b64 = _get(dados, "nfseXmlGZipB64")
        if status not in (200, 201) or not chave or not b64:
            raise SefinErro("A Sefin recusou a DPS", _mensagens(dados, "erros", "erro") or [json.dumps(dados, ensure_ascii=False)[:500]], status)
        return NotaGerada(chave, ungzip_b64(b64), _mensagens(dados, "alertas"), dados)

    def chave_da_dps(self, id_dps: str) -> str | None:
        """Se essa DPS já virou nota, devolve a chave; se não, None."""
        status, dados = self._req("GET", f"{self.base}/dps/{id_dps}", "consultar_dps")
        if status == 404:
            return None
        if status != 200:
            raise SefinErro("Falha ao consultar a DPS", _mensagens(dados, "erros", "erro"), status)
        return _get(dados, "chaveAcesso")

    def baixar_nfse(self, chave: str) -> NotaGerada:
        status, dados = self._req("GET", f"{self.base}/nfse/{chave}", "consultar_nfse")
        b64 = _get(dados, "nfseXmlGZipB64")
        if status != 200 or not b64:
            raise SefinErro("Falha ao baixar a NFS-e", _mensagens(dados, "erros", "erro"), status)
        return NotaGerada(chave, ungzip_b64(b64), [], dados)


def _sem_xml(dados: Any) -> Any:
    """Tira o XML compactado do log (fica salvo em arquivo próprio) e decodifica para leitura."""
    if not isinstance(dados, dict):
        return dados
    out = {}
    for k, v in dados.items():
        if k.lower().endswith("gzipb64") and isinstance(v, str):
            try:
                out[k] = ungzip_b64(v).decode("utf-8")
            except Exception:  # noqa: BLE001
                out[k] = "(conteúdo não decodificado)"
        else:
            out[k] = v
    return out
