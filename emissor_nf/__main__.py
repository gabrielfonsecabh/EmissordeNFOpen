"""Linha de comando do Emissor de NF Open Source.

  emissor painel                         abre o painel no navegador (o jeito mais fácil)
  emissor status                         certificados, empresas e pendências
  emissor exemplo                        gera um PDF fictício para ver o modelo
  emissor certificado adicionar ARQ.pfx  cadastra um certificado A1 (pede a senha)
  emissor certificado listar | testar ID [--producao] | remover ID
  emissor empresa listar | exportar ID ARQ.json
  emissor importar ARQ.json [--certificado ID]
  emissor emitir --empresa X --modelo "Nome"   [--producao] [--sim] ...
  emissor notas [--empresa X]
  emissor verificar [ID]                 confere com a Sefin as emissões pendentes
  emissor pdf NOTA.xml [--empresa X]     refaz o PDF de uma nota a partir do XML

Por padrão o `emitir` usa HOMOLOGAÇÃO (teste). Produção só com --producao.
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from datetime import date, datetime
from pathlib import Path

from . import NOME, SITE, __version__
from . import certificados as CERT
from . import config as C
from . import danfse, db, emissao, exemplo, perfis
from .documentos import formatar_documento, limpar


def _banner() -> None:
    print(f"{NOME} v{__version__} · feito pela TechZyon · {SITE}")


def _empresa(conn, ref: str) -> dict:
    ref = (ref or "").strip()
    if ref.isdigit() and (e := db.obter(conn, "empresas", int(ref))):
        return e
    r = conn.execute("select * from empresas where cnpj = ? or lower(apelido) = lower(?)",
                     (limpar(ref), ref)).fetchone()
    if not r:
        sys.exit(f"Empresa '{ref}' não encontrada. Veja: emissor empresa listar")
    return dict(r)


def _mes(txt: str | None) -> str | None:
    if not txt:
        return None
    try:
        return datetime.strptime(txt, "%m/%Y").strftime("%Y-%m")
    except ValueError:
        sys.exit(f"Mês inválido: {txt!r}. Use MM/AAAA.")


def _data(txt: str | None) -> date | None:
    if not txt:
        return None
    try:
        return datetime.strptime(txt, "%d/%m/%Y").date()
    except ValueError:
        sys.exit(f"Data inválida: {txt!r}. Use DD/MM/AAAA.")


def cmd_painel(conn, a):
    from .painel.app import rodar
    rodar(porta=a.porta, abrir=not a.sem_navegador)


def cmd_status(conn, a):
    _banner()
    print(f"Dados em: {C.DIR_DADOS}")
    certs = db.listar(conn, "certificados")
    print(f"\nCertificados ({len(certs)}):")
    for c in certs:
        senha = "senha no cofre" if CERT.ler_senha(c["id"]) else "SEM SENHA no cofre"
        print(f"  [{c['id']}] {c['apelido']}  {formatar_documento(c['documento'])}  válido até {c['valido_ate']}  ({senha})")
    emps = db.listar(conn, "empresas")
    print(f"\nEmpresas ({len(emps)}):")
    for e in emps:
        n = emissao.proximo_numero(conn, e["id"], C.PRODUCAO, e["serie_dps"])
        print(f"  [{e['id']}] {e['apelido']}  {formatar_documento(e['cnpj'])}  certificado {e['certificado_id'] or '-'}  "
              f"próxima DPS de produção {n}")
    pend = emissao.pendentes(conn)
    if pend:
        print(f"\nATENÇÃO: {len(pend)} emissão(ões) para conferir com a Sefin: emissor verificar")


def cmd_exemplo(conn, a):
    print(f"PDF fictício gerado (nada foi emitido): {exemplo.gerar()}")


def cmd_certificado(conn, a):
    if a.acao == "listar":
        for c in db.listar(conn, "certificados"):
            print(f"[{c['id']}] {c['apelido']}  {c['titular']}  {formatar_documento(c['documento'])}  até {c['valido_ate']}")
    elif a.acao == "adicionar":
        if not a.alvo:
            sys.exit("Informe o arquivo .pfx: emissor certificado adicionar caminho/do/certificado.pfx")
        arq = Path(a.alvo).expanduser()
        if not arq.exists():
            sys.exit(f"Arquivo não encontrado: {arq}")
        senha = getpass.getpass("Senha do certificado (não aparece enquanto digita): ")
        try:
            reg = CERT.importar(conn, arq.read_bytes(), senha, a.apelido)
        except CERT.CertificadoErro as exc:
            sys.exit(str(exc))
        print(f"Certificado [{reg['id']}] '{reg['apelido']}' cadastrado, válido até {reg['valido_ate']}.")
        if not reg["senha_no_cofre"]:
            print(f"ATENÇÃO: cofre de senhas indisponível. Antes de emitir, defina EMISSOR_SENHA_CERT_{reg['id']}.")
    elif a.acao == "testar":
        from .sefin import Sefin, SefinErro
        amb = C.PRODUCAO if a.producao else C.HOMOLOGACAO
        try:
            cert = CERT.carregar(conn, int(a.alvo))
            doc = limpar(cert.documento or "").ljust(14, "0")[:14]
            Sefin(amb, cert).chave_da_dps(f"DPS00000002{doc}49999{'9' * 15}")
        except (CERT.CertificadoErro, SefinErro, ValueError, TypeError) as exc:
            sys.exit(f"Teste falhou: {exc}")
        print(f"Conexão com a Sefin ({C.nome_ambiente(amb)}) OK: o certificado foi aceito.")
    elif a.acao == "remover":
        CERT.remover(conn, int(a.alvo))
        print("Certificado removido (arquivo e senha apagados).")


def cmd_empresa(conn, a):
    if a.acao == "listar":
        for e in db.listar(conn, "empresas"):
            print(f"[{e['id']}] {e['apelido']}  {e['razao_social']}  {formatar_documento(e['cnpj'])}  {e['municipio']}/{e['uf']}")
    elif a.acao == "exportar":
        e = _empresa(conn, a.alvo)
        destino = Path(a.arquivo or f"perfil-{e['cnpj']}.json")
        destino.write_text(json.dumps(perfis.exportar(conn, e["id"]), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Perfil salvo em {destino} (sem certificado e sem senha).")


def cmd_importar(conn, a):
    try:
        eid = perfis.importar(conn, json.loads(Path(a.arquivo).read_text(encoding="utf-8")), a.certificado)
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        sys.exit(f"Não deu para importar: {exc}")
    print(f"Empresa [{eid}] importada.")


def _imprimir_previa(prev: emissao.Previa) -> None:
    print("\n" + "=" * 72)
    print(f"  PRÉVIA  [{C.nome_ambiente(prev.pedido.ambiente)}]")
    print("=" * 72)
    print(f"  Prestador : {prev.empresa['razao_social']} ({formatar_documento(prev.empresa['cnpj'])})")
    print(f"  Tomador   : {prev.cliente['razao_social']} ({formatar_documento(prev.cliente['documento'])})")
    print(f"  Serviço   : {prev.servico['nome']} ({prev.servico['cod_trib_nacional']})")
    print(f"  Valor     : {danfse.brl(prev.valor)}")
    print(f"  Competência {prev.competencia:%d/%m/%Y} · série {prev.empresa['serie_dps']} · DPS {prev.n_dps_previsto} (previsto)")
    print(f"  Certificado: {(prev.certificado or {}).get('apelido', '-')}")
    print(f"  Descrição : {prev.descricao}")
    for x in prev.avisos:
        print(f"  AVISO: {x}")
    for x in prev.bloqueios:
        print(f"  BLOQUEADO: {x}")
    print("=" * 72)


def cmd_emitir(conn, a):
    emp = _empresa(conn, a.empresa)
    modelo = cliente = servico = None
    if a.modelo:
        r = conn.execute("select * from modelos where empresa_id = ? and lower(nome) = lower(?) and ativo = 1",
                         (emp["id"], a.modelo)).fetchone()
        if not r:
            sys.exit(f"Modelo '{a.modelo}' não encontrado nesta empresa.")
        modelo = dict(r)
        cliente, servico = modelo["cliente_id"], modelo["servico_id"]
    if a.cliente:
        r = conn.execute("select id from clientes where empresa_id = ? and documento = ?", (emp["id"], limpar(a.cliente))).fetchone()
        if not r:
            sys.exit(f"Cliente {a.cliente} não cadastrado nesta empresa.")
        cliente = r["id"]
    if a.servico:
        r = conn.execute("select id from servicos where empresa_id = ? and lower(nome) = lower(?)", (emp["id"], a.servico)).fetchone()
        if not r:
            sys.exit(f"Serviço '{a.servico}' não cadastrado nesta empresa.")
        servico = r["id"]
    if not cliente or not servico:
        sys.exit("Informe --modelo, ou --cliente e --servico.")
    p = emissao.Pedido(
        empresa_id=emp["id"], cliente_id=cliente, servico_id=servico, valor=a.valor, descricao=a.descricao,
        ambiente=C.PRODUCAO if a.producao else C.HOMOLOGACAO, modelo_id=(modelo or {}).get("id"),
        mes_referencia=_mes(a.mes_ref), data_pagamento=_data(a.pagamento), competencia=_data(a.competencia),
        certificado_id=a.certificado)
    prev = emissao.preparar(conn, p, permitir_repetida=a.permitir_repetida, forcar_valor=a.forcar_valor)
    _imprimir_previa(prev)
    if prev.bloqueios:
        sys.exit("Nada foi enviado.")
    if a.so_previa:
        print("  Só prévia: nada foi enviado.")
        return
    if not a.sim:
        pedido = "EMITIR" if p.ambiente == C.PRODUCAO else "s"
        if input(f"  Digite {pedido} para confirmar: ").strip().upper() != pedido.upper():
            sys.exit("Cancelado. Nada foi enviado.")
    try:
        e = emissao.emitir(conn, p, permitir_repetida=a.permitir_repetida, forcar_valor=a.forcar_valor)
    except (emissao.EmissaoErro, CERT.CertificadoErro) as exc:
        sys.exit(f"Não emitida: {exc}")
    _imprimir_resultado(e)


def _imprimir_resultado(e: dict) -> None:
    print()
    if e["status"] == "emitida":
        print(f"  NOTA EMITIDA  NFS-e nº {e['numero_nfse']}  chave {e['chave']}")
        print(f"  PDF: {e['pdf_path']}\n  XML: {e['xml_path']}")
    elif e["status"] == "verificar":
        print("  NÃO CONFIRMADA: a Sefin não respondeu. Rode 'emissor verificar' daqui a alguns minutos.")
    else:
        print(f"  {e['status'].upper()}:")
    for m in db.de_json(e["mensagens_json"], []):
        print(f"    {m}")
    if e["status"] == "rejeitada":
        sys.exit(1)


def cmd_notas(conn, a):
    sql = "select e.*, em.apelido empresa from emissoes e join empresas em on em.id = e.empresa_id"
    args: tuple = ()
    if a.empresa:
        sql += " where e.empresa_id = ?"
        args = (_empresa(conn, a.empresa)["id"],)
    for e in conn.execute(sql + " order by e.id desc limit 50", args):
        amb = "TESTE " if e["ambiente"] == C.HOMOLOGACAO else ""
        print(f"[{e['id']}] {amb}{e['status']:<10} NFS-e {e['numero_nfse'] or '-':<6} {e['empresa']:<20} "
              f"{danfse.brl(e['valor']):>14}  ref {e['mes_referencia'] or '-'}  {e['pdf_path'] or ''}")


def cmd_verificar(conn, a):
    ids = [int(a.id)] if a.id else [x["id"] for x in emissao.pendentes(conn)]
    if not ids:
        print("Nada pendente.")
    for i in ids:
        try:
            _imprimir_resultado(emissao.verificar(conn, i))
        except (emissao.EmissaoErro, CERT.CertificadoErro) as exc:
            print(f"[{i}] {exc}")


def cmd_pdf(conn, a):
    xml = Path(a.xml)
    marca = db.de_json(_empresa(conn, a.empresa)["marca_json"]) if a.empresa else None
    print(f"PDF gerado: {danfse.gerar(xml.read_bytes(), xml.with_suffix('.pdf'), marca)}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="emissor", description=f"{NOME} (TechZyon, {SITE})")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("painel", help="abre o painel no navegador")
    p.add_argument("--porta", type=int, default=8765)
    p.add_argument("--sem-navegador", action="store_true")
    sub.add_parser("status")
    sub.add_parser("exemplo")
    p = sub.add_parser("certificado")
    p.add_argument("acao", choices=["adicionar", "listar", "testar", "remover"])
    p.add_argument("alvo", nargs="?", help="arquivo .pfx (adicionar) ou id (testar/remover)")
    p.add_argument("--apelido")
    p.add_argument("--producao", action="store_true", help="testar contra a produção (padrão: homologação)")
    p = sub.add_parser("empresa")
    p.add_argument("acao", choices=["listar", "exportar"])
    p.add_argument("alvo", nargs="?")
    p.add_argument("arquivo", nargs="?")
    p = sub.add_parser("importar")
    p.add_argument("arquivo")
    p.add_argument("--certificado", type=int)
    p = sub.add_parser("emitir")
    p.add_argument("--empresa", required=True, help="id, apelido ou CNPJ")
    p.add_argument("--modelo")
    p.add_argument("--cliente", help="CNPJ/CPF do cliente cadastrado")
    p.add_argument("--servico", help="nome do serviço cadastrado")
    p.add_argument("--valor")
    p.add_argument("--descricao")
    p.add_argument("--mes-ref", help="MM/AAAA")
    p.add_argument("--pagamento", help="DD/MM/AAAA")
    p.add_argument("--competencia", help="DD/MM/AAAA (padrão: hoje)")
    p.add_argument("--certificado", type=int)
    p.add_argument("--producao", action="store_true", help="nota de verdade (padrão: homologação)")
    p.add_argument("--so-previa", action="store_true")
    p.add_argument("--sim", action="store_true", help="não pede confirmação digitada")
    p.add_argument("--permitir-repetida", action="store_true")
    p.add_argument("--forcar-valor", action="store_true")
    p = sub.add_parser("notas")
    p.add_argument("--empresa")
    p = sub.add_parser("verificar")
    p.add_argument("id", nargs="?")
    p = sub.add_parser("pdf")
    p.add_argument("xml")
    p.add_argument("--empresa")
    a = ap.parse_args(argv)

    conn = db.conectar()
    try:
        {"painel": cmd_painel, "status": cmd_status, "exemplo": cmd_exemplo, "certificado": cmd_certificado,
         "empresa": cmd_empresa, "importar": cmd_importar, "emitir": cmd_emitir, "notas": cmd_notas,
         "verificar": cmd_verificar, "pdf": cmd_pdf}[a.cmd](conn, a)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
