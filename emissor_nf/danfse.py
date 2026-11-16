"""DANFSe (PDF da nota) gerado a partir do XML oficial da NFS-e.

A Sefin suspendeu a geração de PDF pela API em 03/08/2026, então cada emissor monta o seu.
O documento fiscal é o XML; o PDF é a representação para leitura, com QR Code da consulta pública.

Marca: por padrão sai com a identidade da TechZyon ("Emissor de NF Open Source"). Cada empresa
pode ter a própria marca (nome, logo, cores, contatos) no cadastro. Os créditos do projeto ficam
numa linha discreta no rodapé; veja CREDITOS-E-MARCA.md para o que a licença pede.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from lxml import etree
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from . import config as C
from .documentos import formatar_cep, formatar_documento, formatar_telefone

NS = {"n": "http://www.sped.fazenda.gov.br/nfse"}

MARCA_PADRAO = {
    "nome": "TechZyon",
    "subtitulo": "Emissor de NF Open Source",
    "slogan": "Diagnóstico antes da solução.",
    "site": "techzyon.com.br",
    "contato": "",
    "logo": "",
    "icone": "techzyon",
    "cor_texto": "#101010",
    "cor_secundaria": "#4a4a4a",
    "cor_acento": "#1d4ed8",
    "cor_linha": "#e4e4e4",
    "creditos": True,
}
CREDITOS = "Gerado com o Emissor de NF Open Source, criado pela TechZyon (techzyon.com.br)."

_FONTES = {
    "Sans": "IBMPlexSans-Regular.ttf",
    "Sans-Medium": "IBMPlexSans-Medium.ttf",
    "Sans-SemiBold": "IBMPlexSans-SemiBold.ttf",
    "Mono": "IBMPlexMono-Regular.ttf",
    "Mono-Medium": "IBMPlexMono-Medium.ttf",
}

REGIME = {
    "1": "Não optante do Simples Nacional",
    "2": "Simples Nacional, MEI",
    "3": "Simples Nacional, ME/EPP",
}


def marca_efetiva(marca: dict | None) -> dict:
    """Mistura a marca da empresa com o padrão. Empresa com nome próprio deixa de usar o ícone da TechZyon."""
    m = dict(MARCA_PADRAO)
    if marca:
        proprios = {k: v for k, v in marca.items() if v not in (None, "")}
        if proprios.get("nome") and proprios.get("nome") != MARCA_PADRAO["nome"]:
            m.update({"subtitulo": "", "slogan": "", "site": "", "icone": "inicial"})
        m.update(proprios)
        if "creditos" in marca:
            m["creditos"] = bool(marca["creditos"])
    return m


def _registrar_fontes() -> None:
    for nome, arq in _FONTES.items():
        if nome not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(nome, str(C.DIR_FONTES / arq)))


# --- leitura do XML ---------------------------------------------------------------------------

def _t(raiz, caminho: str) -> str:
    el = raiz.find(caminho, NS)
    return (el.text or "").strip() if el is not None and el.text else ""


def extrair(xml: bytes) -> dict:
    r = etree.fromstring(xml)
    inf = r.find("n:infNFSe", NS)
    dps = inf.find("n:DPS/n:infDPS", NS)
    doc_toma = _t(dps, "n:toma/n:CNPJ") or _t(dps, "n:toma/n:CPF")
    return {
        "chave": inf.get("Id", "")[3:],
        "numero": _t(inf, "n:nNFSe"),
        "dh_proc": _t(inf, "n:dhProc"),
        "amb": _t(dps, "n:tpAmb"),
        "dh_emi": _t(dps, "n:dhEmi"),
        "competencia": _t(dps, "n:dCompet"),
        "serie": _t(dps, "n:serie"),
        "n_dps": _t(dps, "n:nDPS"),
        "emit_nome": _t(inf, "n:emit/n:xNome"),
        "emit_doc": _t(inf, "n:emit/n:CNPJ") or _t(inf, "n:emit/n:CPF"),
        "emit_im": _t(inf, "n:emit/n:IM"),
        "emit_end": ", ".join(x for x in [
            _t(inf, "n:emit/n:enderNac/n:xLgr"), _t(inf, "n:emit/n:enderNac/n:nro"),
            _t(inf, "n:emit/n:enderNac/n:xBairro")] if x),
        "emit_cep": _t(inf, "n:emit/n:enderNac/n:CEP"),
        "emit_uf": _t(inf, "n:emit/n:enderNac/n:UF"),
        "loc_emi": _t(inf, "n:xLocEmi"),
        "toma_nome": _t(dps, "n:toma/n:xNome"),
        "toma_doc": doc_toma,
        "toma_end": ", ".join(x for x in [
            _t(dps, "n:toma/n:end/n:xLgr"), _t(dps, "n:toma/n:end/n:nro"),
            _t(dps, "n:toma/n:end/n:xCpl"), _t(dps, "n:toma/n:end/n:xBairro")] if x),
        "toma_cep": _t(dps, "n:toma/n:end/n:endNac/n:CEP"),
        "toma_email": _t(dps, "n:toma/n:email"),
        "toma_fone": _t(dps, "n:toma/n:fone"),
        "c_trib_nac": _t(dps, "n:serv/n:cServ/n:cTribNac"),
        "c_trib_mun": _t(dps, "n:serv/n:cServ/n:cTribMun"),
        "c_nbs": _t(dps, "n:serv/n:cServ/n:cNBS"),
        "x_trib_nac": _t(inf, "n:xTribNac"),
        "x_trib_mun": _t(inf, "n:xTribMun"),
        "descricao": _t(dps, "n:serv/n:cServ/n:xDescServ"),
        "loc_prest": _t(inf, "n:xLocPrestacao"),
        "loc_incid": _t(inf, "n:xLocIncid"),
        "v_serv": _t(dps, "n:valores/n:vServPrest/n:vServ"),
        "v_liq": _t(inf, "n:valores/n:vLiq"),
        "p_tot_sn": _t(dps, "n:valores/n:trib/n:totTrib/n:pTotTribSN"),
        "ret_iss": _t(dps, "n:valores/n:trib/n:tribMun/n:tpRetISSQN"),
        "op_simples": _t(dps, "n:prest/n:regTrib/n:opSimpNac"),
    }


# --- formatação -------------------------------------------------------------------------------

def brl(v) -> str:
    if v in (None, ""):
        return "-"
    s = f"{Decimal(str(v)):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _data(iso: str, com_hora: bool = False) -> str:
    if not iso:
        return "-"
    try:
        d = datetime.fromisoformat(iso)
        return d.strftime("%d/%m/%Y %H:%M" if com_hora else "%d/%m/%Y")
    except ValueError:
        return iso


def _chave_em_grupos(chave: str) -> str:
    return " ".join(chave[i:i + 4] for i in range(0, len(chave), 4))


# --- desenho ----------------------------------------------------------------------------------

class _Folha:
    def __init__(self, c: canvas.Canvas, m: dict):
        self.c = c
        self.m = m
        self.texto = HexColor(m["cor_texto"])
        self.sec = HexColor(m["cor_secundaria"])
        self.acento = HexColor(m["cor_acento"])
        self.linha = HexColor(m["cor_linha"])

    def rotulo(self, x, y, txt, cor=None):
        self.c.setFillColor(cor or self.sec)
        self.c.setFont("Mono", 6.4)
        self.c.drawString(x, y, txt.upper(), charSpace=0.5)

    def valor(self, x, y, txt, tam=9.2, fonte="Sans", cor=None, largura=None):
        self.c.setFillColor(cor or self.texto)
        self.c.setFont(fonte, tam)
        if largura:
            while txt and pdfmetrics.stringWidth(txt, fonte, tam) > largura:
                txt = txt[:-2] + "…"
        self.c.drawString(x, y, txt)

    def multilinha(self, x, y, txt, largura, tam=8.6, fonte="Sans", passo=11, max_linhas=2, cor=None):
        linhas = simpleSplit(txt or "-", fonte, tam, largura) or ["-"]
        if len(linhas) > max_linhas:
            linhas = linhas[:max_linhas]
            ult = linhas[-1]
            while pdfmetrics.stringWidth(ult + "…", fonte, tam) > largura:
                ult = ult[:-1]
            linhas[-1] = ult + "…"
        for i, ln in enumerate(linhas):
            self.valor(x, y - i * passo, ln, tam=tam, fonte=fonte, cor=cor)
        return y - (len(linhas) - 1) * passo

    def h(self, x1, x2, y, cor=None, esp=0.6):
        self.c.setStrokeColor(cor or self.linha)
        self.c.setLineWidth(esp)
        self.c.line(x1, y, x2, y)

    def v(self, x, y1, y2):
        self.c.setStrokeColor(self.linha)
        self.c.setLineWidth(0.6)
        self.c.line(x, y1, x, y2)

    def celulas(self, x, larg, y, itens, alt=30, pesos=None):
        pesos = pesos or [1] * len(itens)
        total = sum(pesos)
        cx = x
        for i, ((rot, val), p) in enumerate(zip(itens, pesos)):
            w = larg * p / total
            if i:
                self.v(cx, y, y - alt)
            pad = 0 if i == 0 else 10
            self.rotulo(cx + pad, y - 11, rot)
            self.valor(cx + pad, y - 23, val or "-", largura=w - pad - 6)
            cx += w
        self.h(x, x + larg, y - alt)
        return y - alt

    def icone(self, x, y, lado):
        m, c = self.m, self.c
        logo = m.get("logo")
        logo = C.resolver(logo) if logo else None
        if logo and logo.exists():
            try:
                img = ImageReader(str(logo))
                iw, ih = img.getSize()
                esc = lado / max(iw, ih)
                c.drawImage(img, x, y + (lado - ih * esc) / 2, iw * esc, ih * esc, mask="auto")
                return
            except Exception:  # noqa: BLE001 (logo inválido não pode impedir o PDF da nota)
                pass
        c.setFillColor(self.texto)
        c.rect(x, y, lado, lado, stroke=0, fill=1)
        if m.get("icone") == "techzyon":
            c.setFillColor(HexColor("#ffffff"))
            c.rect(x + lado * 0.24, y + lado * 0.68, lado * 0.52, lado * 0.13, stroke=0, fill=1)
            c.rect(x + lado * 0.435, y + lado * 0.24, lado * 0.13, lado * 0.47, stroke=0, fill=1)
        else:
            c.setFillColor(HexColor("#ffffff"))
            c.setFont("Sans-SemiBold", lado * 0.55)
            c.drawCentredString(x + lado / 2, y + lado * 0.3, (m.get("nome") or "?")[:1].upper())
        c.setFillColor(self.acento)
        c.rect(x, y, lado, lado * 0.09, stroke=0, fill=1)

    def wordmark(self, x, y, nome, tam=19):
        c = self.c
        c.setFillColor(self.texto)
        c.setFont("Sans-SemiBold", tam)
        c.drawString(x, y, nome, charSpace=-0.35)
        c.setFillColor(self.acento)
        c.rect(x + 0.5, y - 5.5, min(tam * 1.15, pdfmetrics.stringWidth(nome, "Sans-SemiBold", tam)), 3, stroke=0, fill=1)


def gerar(xml: bytes, destino: Path, marca: dict | None = None, aviso: str | None = None) -> Path:
    """Gera o PDF em `destino`. `aviso` imprime faixa e marca d'água (ex.: MODELO, HOMOLOGAÇÃO)."""
    _registrar_fontes()
    m = marca_efetiva(marca)
    d = extrair(xml)
    if aviso is None and d["amb"] == C.HOMOLOGACAO:
        aviso = "HOMOLOGAÇÃO · SEM VALOR FISCAL"

    W, H = A4
    M = 38
    X2 = W - M
    LARG = X2 - M
    c = canvas.Canvas(str(destino), pagesize=A4)
    c.setTitle(f"NFS-e {d['numero']}")
    c.setAuthor(m["nome"])
    c.setCreator(CREDITOS)
    f = _Folha(c, m)

    if aviso:
        c.saveState()
        c.setFillColor(f.linha)
        c.setFillAlpha(0.45)
        c.setFont("Sans-SemiBold", 54)
        c.translate(W / 2, H / 2)
        c.rotate(35)
        c.drawCentredString(0, 0, aviso.split("·")[0].strip())
        c.restoreState()

    # Cabeçalho
    y = H - M
    f.icone(M, y - 30, 30)
    f.wordmark(M + 42, y - 19, m["nome"])
    if m.get("subtitulo"):
        f.rotulo(M + 42, y - 31, m["subtitulo"])
    c.setFillColor(f.sec)
    c.setFont("Mono", 6.4)
    c.drawRightString(X2, y - 6, "NOTA FISCAL DE SERVIÇO ELETRÔNICA", charSpace=0.5)
    c.setFillColor(f.texto)
    c.setFont("Sans-Medium", 24)
    num = f"Nº {d['numero']}"
    c.drawRightString(X2, y - 30, num, charSpace=-0.4)
    c.setFillColor(f.acento)
    c.setFont("Mono-Medium", 6.4)
    c.drawRightString(X2 - pdfmetrics.stringWidth(num, "Sans-Medium", 24) - 12, y - 30, "NFS-e", charSpace=0.5)
    y -= 44
    f.h(M, X2, y, cor=f.texto, esp=1.1)

    if aviso:
        y -= 16
        c.setFillColor(f.acento)
        c.rect(M, y - 3, LARG, 15, stroke=0, fill=1)
        c.setFillColor(HexColor("#ffffff"))
        c.setFont("Mono-Medium", 7.2)
        c.drawCentredString(W / 2, y + 1.5, aviso, charSpace=1.2)
        y -= 6

    y = f.celulas(M, LARG, y, [
        ("Emissão", _data(d["dh_emi"], True)),
        ("Competência", _data(d["competencia"])),
        ("Série / Nº DPS", f"{d['serie']} / {d['n_dps']}"),
        ("Processamento", _data(d["dh_proc"], True)),
    ])

    # Chave e QR Code
    qr_lado = 62
    f.rotulo(M, y - 13, "Chave de acesso")
    f.valor(M, y - 27, _chave_em_grupos(d["chave"]), tam=9.6, fonte="Mono")
    f.rotulo(M, y - 47, "Consulte a autenticidade")
    f.valor(M, y - 59, "nfse.gov.br/ConsultaPublica  ·  aponte a câmera para o QR Code", tam=8, cor=f.sec)
    qr = QrCodeWidget(C.URL_CONSULTA_PUBLICA.format(chave=d["chave"]), barBorder=0)
    qr.barFillColor = f.texto
    bx0, by0, bx1, by1 = qr.getBounds()
    dw = Drawing(qr_lado, qr_lado, transform=[qr_lado / (bx1 - bx0), 0, 0, qr_lado / (by1 - by0), 0, 0])
    dw.add(qr)
    renderPDF.draw(dw, c, X2 - qr_lado, y - qr_lado - 7)
    y -= qr_lado + 14
    f.h(M, X2, y)

    # Prestador | Tomador
    meio = M + LARG / 2
    topo = y

    def bloco(x, larg, titulo, linhas, destaque):
        yy = topo - 14
        f.rotulo(x, yy, titulo, cor=f.acento if destaque else None)
        yy -= 15
        yy = f.multilinha(x, yy, linhas[0], larg, tam=10, fonte="Sans-Medium", passo=12.5)
        yy -= 14
        for rot, val in linhas[1:]:
            f.rotulo(x, yy, rot)
            yy = f.multilinha(x + 58, yy, val, larg - 58)
            yy -= 12.5
        return yy

    y1 = bloco(M, LARG / 2 - 14, "Prestador do serviço", [
        d["emit_nome"],
        ("CNPJ/CPF", formatar_documento(d["emit_doc"])),
        ("Insc. mun.", d["emit_im"] or "-"),
        ("Endereço", d["emit_end"] or "-"),
        ("Município", f"{d['loc_emi']}{' / ' + d['emit_uf'] if d['emit_uf'] else ''}  ·  CEP {formatar_cep(d['emit_cep'])}"),
    ], True)
    y2 = bloco(meio + 12, LARG / 2 - 12, "Tomador do serviço", [
        d["toma_nome"],
        ("CNPJ/CPF", formatar_documento(d["toma_doc"])),
        ("Endereço", f"{d['toma_end'] or '-'}  ·  CEP {formatar_cep(d['toma_cep'])}"),
        ("E-mail", d["toma_email"] or "-"),
        ("Telefone", formatar_telefone(d["toma_fone"]) or "-"),
    ], False)
    y = min(y1, y2) - 4
    f.v(meio, topo, y)
    f.h(M, X2, y)

    # Serviço
    y = f.celulas(M, LARG, y, [("Tributação nacional", f"{d['c_trib_nac']}  {d['x_trib_nac']}")])
    y = f.celulas(M, LARG, y, [
        ("Tributação municipal", f"{d['c_trib_mun']}  {d['x_trib_mun']}".strip()),
        ("NBS", d["c_nbs"] or "-"),
    ], pesos=[3, 1])
    y = f.celulas(M, LARG, y, [
        ("Local da prestação", d["loc_prest"] or "-"),
        ("Município de incidência do ISSQN", d["loc_incid"] or "-"),
    ])

    # Descrição
    f.rotulo(M, y - 13, "Descrição do serviço")
    yy = y - 28
    c.setFillColor(f.texto)
    c.setFont("Sans", 9.6)
    for ln in simpleSplit(d["descricao"], "Sans", 9.6, LARG):
        c.drawString(M, yy, ln)
        yy -= 13
    y = yy - 6
    f.h(M, X2, y)

    # Valores
    y = f.celulas(M, LARG, y, [
        ("Valor do serviço", brl(d["v_serv"])),
        ("Descontos / deduções", "R$ 0,00"),
        ("ISSQN", "Não retido" if d["ret_iss"] in ("1", "") else "Retido pelo tomador"),
        ("Tributos aprox. (Simples)", f"{d['p_tot_sn'].replace('.', ',')}%" if d["p_tot_sn"] else "-"),
    ])
    alt = 46
    c.setFillColor(f.acento)
    c.rect(M, y - alt, 3, alt, stroke=0, fill=1)
    f.rotulo(M + 14, y - 15, "Valor líquido da NFS-e")
    c.setFillColor(f.texto)
    c.setFont("Sans-Medium", 21)
    c.drawString(M + 14, y - 38, brl(d["v_liq"]), charSpace=-0.3)
    f.rotulo(meio + 12, y - 15, "Regime tributário")
    f.valor(meio + 12, y - 27, REGIME.get(d["op_simples"], "-"), tam=8.8)
    y -= alt
    f.h(M, X2, y, cor=f.texto, esp=1.1)

    # Rodapé
    rod = M + 34
    f.h(M, X2, rod + 26)
    f.icone(M, rod - 2, 16)
    c.setFillColor(f.texto)
    c.setFont("Sans-SemiBold", 9.5)
    c.drawString(M + 24, rod + 9, m["nome"], charSpace=-0.2)
    if m.get("slogan"):
        c.setFillColor(f.sec)
        c.setFont("Sans", 8.2)
        c.drawString(M + 24 + pdfmetrics.stringWidth(m["nome"], "Sans-SemiBold", 9.5) + 8, rod + 9, m["slogan"])
    if m.get("subtitulo"):
        f.rotulo(M + 24, rod - 1, m["subtitulo"])
    c.setFillColor(f.sec)
    c.setFont("Mono", 7)
    if m.get("site"):
        c.drawRightString(X2, rod + 9, m["site"])
    if m.get("contato"):
        c.drawRightString(X2, rod - 1, m["contato"])
    c.setFont("Mono", 5.8)
    linha_final = "DANFSe: documento auxiliar gerado a partir do XML oficial da NFS-e (padrão nacional). O documento fiscal é o XML."
    c.drawString(M, M - 2, linha_final)
    if m.get("creditos", True):
        c.drawString(M, M - 10, CREDITOS)

    c.showPage()
    c.save()
    return destino
