"""Fluxo de emissão: prévia, travas, numeração, envio seguro e retomada.

Regras que protegem você (todas testadas em tests/test_emissao.py):
  * A prévia monta e valida a DPS no esquema oficial antes de qualquer envio.
  * O certificado escolhido precisa ser da mesma empresa (mesma raiz de CNPJ) e estar dentro da validade.
  * Valor fora da faixa do modelo e segunda nota de produção para o mesmo cliente no mesmo mês
    de referência são bloqueados, a menos que você libere de propósito.
  * O número da DPS é reservado e gravado ANTES do envio. Se a internet cair no meio, a próxima
    tentativa pergunta à Sefin se aquela DPS já virou nota, em vez de mandar de novo.
  * Nota que já existe na Sefin mas não confere (cliente ou valor diferentes) vira "rejeitada"
    com aviso de conflito de numeração, para você decidir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from lxml import etree

from . import assinatura as A
from . import certificados as CERT
from . import config as C
from . import danfse
from . import db
from . import dps as D
from .documentos import limpar
from .sefin import NotaGerada, Sefin, SefinErro

NS = {"n": D.NS}
SefinFactory = Callable[[str, "CERT.Certificado"], Sefin]


class EmissaoErro(Exception):
    def __init__(self, problemas: list[str]):
        self.problemas = problemas
        super().__init__(" | ".join(problemas))


@dataclass
class Pedido:
    empresa_id: int
    cliente_id: int
    servico_id: int
    valor: Decimal | str | float | None = None
    descricao: str | None = None
    ambiente: str = C.PRODUCAO
    modelo_id: int | None = None
    mes_referencia: str | None = None      # AAAA-MM
    data_pagamento: date | None = None
    competencia: date | None = None        # vazia = data da emissão
    certificado_id: int | None = None      # vazia = certificado padrão da empresa


@dataclass
class Previa:
    pedido: Pedido
    empresa: dict
    cliente: dict
    servico: dict
    modelo: dict | None
    certificado: dict | None
    valor: Decimal | None
    descricao: str
    competencia: date
    leiaute: str
    n_dps_previsto: int
    avisos: list[str] = field(default_factory=list)
    bloqueios: list[str] = field(default_factory=list)
    liberaveis: set[str] = field(default_factory=set)

    @property
    def pode_emitir(self) -> bool:
        return not self.bloqueios


def valor_decimal(v) -> Decimal | None:
    """Aceita 1234, 1234.56, "1.234,56", "R$ 1.234,56". Devolve None se não for número."""
    if v in (None, ""):
        return None
    if isinstance(v, (Decimal, int, float)):
        s = str(v)
    else:
        s = str(v).replace("R$", "").replace(" ", "").strip()
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


_dec = valor_decimal


def _maior_usado(conn, empresa_id: int, ambiente: str, serie: int) -> int:
    r = conn.execute("select max(n_dps) m from emissoes where empresa_id = ? and ambiente = ? and serie = ?",
                     (empresa_id, ambiente, serie)).fetchone()
    return int(r["m"] or 0)


def proximo_numero(conn, empresa_id: int, ambiente: str, serie: int) -> int:
    r = conn.execute("select proximo from numeracao where empresa_id = ? and ambiente = ? and serie = ?",
                     (empresa_id, ambiente, serie)).fetchone()
    return max(int(r["proximo"]) if r else 1, _maior_usado(conn, empresa_id, ambiente, serie) + 1)


def definir_proximo_numero(conn, empresa_id: int, ambiente: str, serie: int, proximo: int) -> None:
    """Para quem já emitiu por outro sistema próprio na mesma série: comece depois do último número usado."""
    usado = _maior_usado(conn, empresa_id, ambiente, serie)
    if int(proximo) <= usado:
        raise ValueError(f"O número {proximo} já foi usado por este emissor. Use {usado + 1} ou maior.")
    if not 1 <= int(proximo) <= 999_999_999_999_999:
        raise ValueError("Número fora da faixa permitida.")
    conn.execute("insert into numeracao (empresa_id, ambiente, serie, proximo) values (?, ?, ?, ?) "
                 "on conflict (empresa_id, ambiente, serie) do update set proximo = excluded.proximo",
                 (empresa_id, ambiente, serie, int(proximo)))


def preparar(conn, p: Pedido, *, permitir_repetida: bool = False, forcar_valor: bool = False) -> Previa:
    bloqueios: list[str] = []
    avisos: list[str] = []
    liberaveis: set[str] = set()

    empresa = db.obter(conn, "empresas", p.empresa_id)
    if not empresa or not empresa["ativo"]:
        raise EmissaoErro(["Empresa não encontrada ou inativa."])
    cliente = db.obter(conn, "clientes", p.cliente_id)
    servico = db.obter(conn, "servicos", p.servico_id)
    modelo = db.obter(conn, "modelos", p.modelo_id) if p.modelo_id else None
    if not cliente or cliente["empresa_id"] != empresa["id"] or not cliente["ativo"]:
        raise EmissaoErro(["Cliente não encontrado, inativo ou de outra empresa."])
    if not servico or servico["empresa_id"] != empresa["id"] or not servico["ativo"]:
        raise EmissaoErro(["Serviço não encontrado, inativo ou de outra empresa."])
    if modelo and modelo["empresa_id"] != empresa["id"]:
        raise EmissaoErro(["Modelo de outra empresa."])

    # Certificado
    cert_id = p.certificado_id or empresa.get("certificado_id")
    cert = db.obter(conn, "certificados", cert_id) if cert_id else None
    if not cert:
        bloqueios.append("Nenhum certificado escolhido para esta empresa. Cadastre um em Certificados e ligue à empresa.")
    else:
        doc_cert = limpar(cert.get("documento"))
        cnpj = limpar(empresa["cnpj"])
        if doc_cert and doc_cert[:8] != cnpj[:8]:
            bloqueios.append(f"O certificado '{cert['apelido']}' é do documento {doc_cert}, mas a empresa é {cnpj}.")
        elif doc_cert and doc_cert != cnpj:
            avisos.append("O certificado é de outro estabelecimento da mesma empresa (mesma raiz de CNPJ).")
        if cert.get("valido_ate") and cert["valido_ate"] < C.agora().date().isoformat():
            bloqueios.append(f"O certificado '{cert['apelido']}' venceu em {cert['valido_ate']}.")
        elif cert.get("valido_ate") and cert["valido_ate"] <= (C.agora().date() + timedelta(days=30)).isoformat():
            avisos.append(f"O certificado vence em {cert['valido_ate']}. Providencie a renovação.")

    # Valor e descrição
    valor = _dec(p.valor) if p.valor not in (None, "") else _dec((modelo or {}).get("valor") or servico.get("valor_padrao"))
    if valor is None or valor <= 0:
        bloqueios.append("Informe um valor maior que zero.")
    if modelo and valor is not None:
        vmin, vmax = _dec(modelo.get("valor_minimo")), _dec(modelo.get("valor_maximo"))
        if (vmin and valor < vmin) or (vmax and valor > vmax):
            msg = f"Valor {danfse.brl(valor)} fora da faixa do modelo ({danfse.brl(vmin)} a {danfse.brl(vmax)})."
            if forcar_valor:
                avisos.append(msg + " Liberado por você.")
            else:
                bloqueios.append(msg)
                liberaveis.add("valor")
    descricao = (p.descricao or "").strip()
    if not descricao:
        descricao = D.render_descricao((modelo or {}).get("descricao_modelo") or servico.get("descricao_padrao") or "",
                                       p.mes_referencia, p.data_pagamento).strip()
    if not descricao:
        bloqueios.append("A descrição do serviço está vazia.")

    # Duplicidade (só produção, só com mês de referência)
    if p.ambiente == C.PRODUCAO and p.mes_referencia:
        dup = conn.execute(
            "select id, numero_nfse, status from emissoes where empresa_id = ? and cliente_id = ? and ambiente = ? "
            "and mes_referencia = ? and status in ('emitida','processando','verificar') order by id limit 1",
            (empresa["id"], cliente["id"], C.PRODUCAO, p.mes_referencia)).fetchone()
        if dup:
            msg = (f"Já existe nota de produção para este cliente em {p.mes_referencia} "
                   f"(emissão {dup['id']}, NFS-e {dup['numero_nfse'] or '-'}, {dup['status']}).")
            if permitir_repetida:
                avisos.append(msg + " Liberado por você.")
            else:
                bloqueios.append(msg)
                liberaveis.add("repetida")

    if p.ambiente == C.HOMOLOGACAO:
        avisos.append("Homologação: a nota é de teste e não tem valor fiscal.")

    agora = C.agora() - timedelta(minutes=1)
    competencia = p.competencia or agora.date()
    lei = D.leiaute(p.ambiente, agora)
    n_prev = proximo_numero(conn, empresa["id"], p.ambiente, empresa["serie_dps"])

    if not bloqueios:
        try:
            el = D.montar(empresa, cliente, servico, D.DadosNota(
                tp_amb=p.ambiente, dh_emi=agora, serie=empresa["serie_dps"], n_dps=n_prev,
                d_compet=competencia, descricao=descricao, valor=valor))
            D.validar(el, lei)
        except D.DpsErro as exc:
            bloqueios.append(str(exc))

    return Previa(p, empresa, cliente, servico, modelo, cert, valor, descricao, competencia, lei, n_prev,
                  avisos, bloqueios, liberaveis)


def _sefin_padrao(ambiente: str, cert: CERT.Certificado) -> Sefin:
    return Sefin(ambiente, cert)


def emitir(conn, p: Pedido, *, permitir_repetida: bool = False, forcar_valor: bool = False,
           senha: str | None = None, sefin_factory: SefinFactory | None = None,
           certificado: CERT.Certificado | None = None) -> dict:
    prev = preparar(conn, p, permitir_repetida=permitir_repetida, forcar_valor=forcar_valor)
    if prev.bloqueios:
        raise EmissaoErro(prev.bloqueios)
    cert = certificado or CERT.carregar(conn, prev.certificado["id"], senha)
    emp = prev.empresa

    with db.transacao(conn):
        serie = int(emp["serie_dps"])
        conn.execute("insert into numeracao (empresa_id, ambiente, serie, proximo) values (?, ?, ?, 1) "
                     "on conflict do nothing", (emp["id"], p.ambiente, serie))
        n = proximo_numero(conn, emp["id"], p.ambiente, serie)
        conn.execute("update numeracao set proximo = ? where empresa_id = ? and ambiente = ? and serie = ?",
                     (n + 1, emp["id"], p.ambiente, serie))
        snapshot = {"empresa": emp, "cliente": prev.cliente, "servico": prev.servico, "modelo": prev.modelo}
        emissao_id = db.inserir(conn, "emissoes", {
            "empresa_id": emp["id"], "certificado_id": prev.certificado["id"], "cliente_id": prev.cliente["id"],
            "servico_id": prev.servico["id"], "modelo_id": (prev.modelo or {}).get("id"), "ambiente": p.ambiente,
            "status": "processando", "valor": str(prev.valor), "descricao": prev.descricao,
            "mes_referencia": p.mes_referencia, "competencia": prev.competencia.isoformat(),
            "snapshot_json": db.para_json(snapshot), "serie": serie, "n_dps": n,
            "id_dps": D.id_dps(emp["cod_municipio"], emp["cnpj"], serie, n), "tentativas": 0})
    return enviar(conn, emissao_id, cert, sefin_factory)


def enviar(conn, emissao_id: int, cert: CERT.Certificado, sefin_factory: SefinFactory | None = None) -> dict:
    """Envia (ou retoma) uma emissão já numerada. Nunca manda de novo uma DPS que já virou nota."""
    e = db.obter(conn, "emissoes", emissao_id)
    snap = db.de_json(e["snapshot_json"])
    emp, cli, srv = snap["empresa"], snap["cliente"], snap["servico"]
    conn.execute("update emissoes set tentativas = tentativas + 1, atualizado_em = datetime('now') where id = ?",
                 (emissao_id,))
    try:
        if limpar(cert.documento or "")[:8] != limpar(emp["cnpj"])[:8]:
            raise D.DpsErro(f"o certificado carregado é do documento {cert.documento}, a nota é do {emp['cnpj']}")
        agora = C.agora() - timedelta(minutes=1)
        dados = D.DadosNota(tp_amb=e["ambiente"], dh_emi=agora, serie=e["serie"], n_dps=e["n_dps"],
                            d_compet=date.fromisoformat(e["competencia"]) if e["competencia"] else agora.date(),
                            descricao=e["descricao"], valor=Decimal(e["valor"]))
        lei = D.leiaute(dados.tp_amb, agora)
        el = D.montar(emp, cli, srv, dados)
        if el.find(f"{{{D.NS}}}infDPS").get("Id") != e["id_dps"]:
            raise D.DpsErro("o identificador da DPS montada difere do reservado")
        D.validar(el, lei)
        assinado = A.assinar(el, cert.chave, cert.cert_pem())
        D.validar(assinado, lei)
        dps_bytes = D.para_bytes(assinado)
        A.verificar(dps_bytes, cert.cert_pem())
        (C.dir_dados("dps") / f"{e['id_dps']}.xml").write_bytes(dps_bytes)

        s = (sefin_factory or _sefin_padrao)(e["ambiente"], cert)
        chave = s.chave_da_dps(e["id_dps"])
        if chave:
            nota = s.baixar_nfse(chave)
            problemas = confere_nota(nota.xml, cli["documento"], Decimal(e["valor"]))
            if problemas:
                raise D.DpsErro("conflito de numeração, esta DPS já gerou uma nota diferente: " + "; ".join(problemas))
        else:
            try:
                nota = s.emitir(dps_bytes)
            except SefinErro as exc:
                if not exc.ambiguo:
                    raise
                chave = s.chave_da_dps(e["id_dps"])
                if not chave:
                    raise
                nota = s.baixar_nfse(chave)
    except SefinErro as exc:
        rejeicao = (exc.status is not None and 400 <= exc.status < 500 and exc.status not in (401, 403, 408, 429)
                    and not any("E0014" in m for m in exc.mensagens))
        return _falhar(conn, emissao_id, "rejeitada" if rejeicao else "verificar", [exc.resumo, *exc.mensagens])
    except (D.DpsErro, CERT.CertificadoErro) as exc:
        return _falhar(conn, emissao_id, "rejeitada", [str(exc)])
    return _guardar(conn, e, emp, nota)


def _falhar(conn, emissao_id: int, status: str, mensagens: list[str]) -> dict:
    conn.execute("update emissoes set status = ?, mensagens_json = ?, atualizado_em = datetime('now') where id = ?",
                 (status, db.para_json(mensagens), emissao_id))
    return db.obter(conn, "emissoes", emissao_id)


def pasta_da_nota(emp: dict, ambiente: str, quando: datetime) -> Path:
    if ambiente == C.HOMOLOGACAO:
        base = C.dir_dados("homologacao", limpar(emp["cnpj"]))
    elif emp.get("pasta_saida"):
        base = Path(emp["pasta_saida"]).expanduser()
    else:
        base = C.dir_dados("notas", limpar(emp["cnpj"]))
    p = base / f"{quando.year}" / f"{quando.month:02d}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _guardar(conn, e: dict, emp: dict, nota: NotaGerada) -> dict:
    info = danfse.extrair(nota.xml)
    dh = datetime.fromisoformat(info["dh_emi"]) if info["dh_emi"] else C.agora()
    pasta = pasta_da_nota(emp, e["ambiente"], dh)
    prefixo = "HOMOLOGACAO_" if e["ambiente"] == C.HOMOLOGACAO else ""
    arq_xml = pasta / f"{prefixo}{nota.chave}.xml"
    arq_pdf = pasta / f"{prefixo}{nota.chave}.pdf"
    arq_xml.write_bytes(nota.xml)
    danfse.gerar(nota.xml, arq_pdf, db.de_json(emp.get("marca_json"), None))
    conn.execute(
        "update emissoes set status = 'emitida', chave = ?, numero_nfse = ?, dh_emissao = ?, xml_path = ?, "
        "pdf_path = ?, mensagens_json = ?, atualizado_em = datetime('now') where id = ?",
        (nota.chave, info["numero"], info["dh_emi"], str(arq_xml), str(arq_pdf),
         db.para_json([str(a) for a in nota.alertas]), e["id"]))
    return db.obter(conn, "emissoes", e["id"])


def confere_nota(xml: bytes, documento_cliente: str, valor: Decimal) -> list[str]:
    r = etree.fromstring(xml)
    inf = r.find("n:infNFSe/n:DPS/n:infDPS", NS)
    doc = inf.findtext("n:toma/n:CNPJ", namespaces=NS) or inf.findtext("n:toma/n:CPF", namespaces=NS) or ""
    v = Decimal(inf.findtext("n:valores/n:vServPrest/n:vServ", namespaces=NS) or "0")
    problemas = []
    if limpar(doc) != limpar(documento_cliente):
        problemas.append(f"cliente da nota é {doc}, o pedido era {limpar(documento_cliente)}")
    if v != Decimal(str(valor)):
        problemas.append(f"valor da nota é {v}, o pedido era {valor}")
    return problemas


def pendentes(conn) -> list[dict]:
    """Emissões que precisam de conferência: 'verificar' ou 'processando' parada há mais de 10 minutos."""
    rows = conn.execute(
        "select * from emissoes where status = 'verificar' or (status = 'processando' and "
        "atualizado_em < datetime('now', '-10 minutes')) order by id").fetchall()
    return [dict(r) for r in rows]


def verificar(conn, emissao_id: int, senha: str | None = None, sefin_factory: SefinFactory | None = None,
              certificado: CERT.Certificado | None = None) -> dict:
    e = db.obter(conn, "emissoes", emissao_id)
    if not e or e["status"] not in ("verificar", "processando"):
        raise EmissaoErro([f"A emissão {emissao_id} não está pendente de conferência."])
    cert = certificado or CERT.carregar(conn, e["certificado_id"], senha)
    conn.execute("update emissoes set status = 'processando' where id = ?", (emissao_id,))
    return enviar(conn, emissao_id, cert, sefin_factory)
