"""Painel local do Emissor de NF Open Source (Flask, server-side, sem build de front-end).

Segurança de um painel local:
  * escuta só em 127.0.0.1 e recusa qualquer Host que não seja localhost (contra DNS rebinding);
  * todo formulário POST leva um token CSRF da sessão;
  * a chave da sessão é aleatória a cada vez que o painel sobe;
  * a senha do certificado vai direto para o cofre do sistema e nunca é gravada no banco nem em log.
"""

from __future__ import annotations

import json
import secrets
from datetime import date, timedelta
from pathlib import Path

import requests
from flask import (Flask, Response, abort, flash, g, jsonify, redirect, render_template, request, send_file,
                   session, url_for)

from .. import NOME, SITE, __version__
from .. import certificados as CERT
from .. import config as C
from .. import danfse, db, emissao, exemplo, formularios as F, perfis
from ..documentos import formatar_cep, formatar_documento, formatar_telefone, limpar, so_digitos
from ..sefin import Sefin, SefinErro

HOSTS_LOCAIS = {"127.0.0.1", "localhost", "[::1]"}


def criar_app(caminho_banco: str | Path | None = None, sefin_factory=None) -> Flask:
    app = Flask(__name__)
    app.config.update(SECRET_KEY=secrets.token_hex(32), MAX_CONTENT_LENGTH=5 * 1024 * 1024,
                      SESSION_COOKIE_SAMESITE="Strict", BANCO=caminho_banco, SEFIN_FACTORY=sefin_factory)

    # --- infraestrutura -------------------------------------------------------------------
    def conn():
        if "conn" not in g:
            g.conn = db.conectar(app.config["BANCO"])
        return g.conn

    @app.teardown_appcontext
    def _fechar(_exc):
        c = g.pop("conn", None)
        if c is not None:
            c.close()

    @app.before_request
    def _seguranca():
        host = (request.host or "").rsplit(":", 1)[0]
        if host not in HOSTS_LOCAIS and not app.testing:
            abort(403)
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(16)
        if request.method == "POST" and request.form.get("csrf") != session["csrf"]:
            abort(400, "Formulário expirado. Volte e tente de novo.")

    @app.context_processor
    def _contexto():
        return {"csrf": session.get("csrf", ""), "NOME": NOME, "SITE": SITE, "VERSAO": __version__,
                "brl": danfse.brl, "doc": formatar_documento, "cep": formatar_cep, "fone": formatar_telefone,
                "AMBIENTES": C.AMBIENTES, "PRODUCAO": C.PRODUCAO, "HOMOLOGACAO": C.HOMOLOGACAO}

    @app.get("/fontes/<nome>")
    def fontes(nome):
        arq = C.DIR_FONTES / Path(nome).name
        if not arq.exists() or arq.suffix != ".ttf":
            abort(404)
        return send_file(arq, mimetype="font/ttf", max_age=86400)

    def empresas_ativas():
        return db.listar(conn(), "empresas", ativo=1)

    def certificados_opcoes():
        return [("", "-")] + [(str(c["id"]), f"{c['apelido']} ({formatar_documento(c['documento'])}, até "
                                             f"{c['valido_ate']})") for c in db.listar(conn(), "certificados")]

    # --- início ---------------------------------------------------------------------------
    @app.get("/")
    def inicio():
        c = conn()
        certs = db.listar(c, "certificados")
        hoje = date.today().isoformat()
        alertas = []
        if not certs:
            alertas.append(("info", "Comece cadastrando o certificado A1 da empresa.", url_for("certificados")))
        if certs and not empresas_ativas():
            alertas.append(("info", "Agora cadastre a empresa que vai emitir.", url_for("empresa_nova")))
        for ct in certs:
            if ct["valido_ate"] and ct["valido_ate"] < hoje:
                alertas.append(("erro", f"O certificado '{ct['apelido']}' venceu em {ct['valido_ate']}.", url_for("certificados")))
            elif ct["valido_ate"] and ct["valido_ate"] <= (date.today() + timedelta(days=30)).isoformat():
                alertas.append(("aviso", f"O certificado '{ct['apelido']}' vence em {ct['valido_ate']}. Providencie a renovação.",
                                url_for("certificados")))
        pend = emissao.pendentes(c)
        if pend:
            alertas.append(("aviso", f"{len(pend)} emissão(ões) precisam de conferência com a Sefin.", url_for("notas")))
        ultimas = c.execute("select e.*, em.apelido empresa, cl.razao_social cliente from emissoes e "
                            "join empresas em on em.id = e.empresa_id left join clientes cl on cl.id = e.cliente_id "
                            "order by e.id desc limit 8").fetchall()
        return render_template("inicio.html", alertas=alertas, ultimas=ultimas, empresas=empresas_ativas(),
                               certs=certs)

    # --- certificados -----------------------------------------------------------------------
    @app.route("/certificados", methods=["GET", "POST"])
    def certificados():
        c = conn()
        if request.method == "POST":
            arq = request.files.get("arquivo")
            senha = request.form.get("senha") or ""
            if not arq or not arq.filename:
                flash("Escolha o arquivo .pfx ou .p12 do certificado.", "erro")
            else:
                try:
                    reg = CERT.importar(c, arq.read(), senha, request.form.get("apelido") or None)
                    msg = (f"Certificado '{reg['apelido']}' já estava cadastrado: arquivo e senha atualizados."
                           if reg["ja_existia"] else
                           f"Certificado '{reg['apelido']}' cadastrado (válido até {reg['valido_ate']}).")
                    if not reg["senha_no_cofre"]:
                        msg += (f" Atenção: o cofre de senhas do sistema não está disponível. Defina a variável "
                                f"EMISSOR_SENHA_CERT_{reg['id']} antes de emitir.")
                    flash(msg, "ok" if reg["senha_no_cofre"] else "aviso")
                    return redirect(url_for("certificados"))
                except CERT.CertificadoErro as exc:
                    flash(str(exc), "erro")
        return render_template("certificados.html", certs=db.listar(c, "certificados"))

    @app.post("/certificados/<int:cid>/remover")
    def certificado_remover(cid):
        c = conn()
        if c.execute("select 1 from empresas where certificado_id = ?", (cid,)).fetchone():
            flash("Este certificado é o padrão de uma empresa. Troque o certificado da empresa antes.", "erro")
        else:
            CERT.remover(c, cid)
            flash("Certificado removido (arquivo e senha apagados).", "ok")
        return redirect(url_for("certificados"))

    @app.post("/certificados/<int:cid>/testar")
    def certificado_testar(cid):
        amb = request.form.get("ambiente") or C.HOMOLOGACAO
        try:
            cert = CERT.carregar(conn(), cid)
            s = (app.config["SEFIN_FACTORY"] or Sefin)(amb, cert)
            cnpj = limpar(cert.documento or "00000000000000").ljust(14, "0")[:14]
            s.chave_da_dps(f"DPS0000000{'2'}{cnpj}49999{'9' * 15}")
            flash(f"Conexão com a Sefin ({C.nome_ambiente(amb)}) funcionando: o certificado foi aceito.", "ok")
        except (CERT.CertificadoErro, SefinErro) as exc:
            flash(f"Teste falhou: {exc}", "erro")
        return redirect(url_for("certificados"))

    # --- empresas ---------------------------------------------------------------------------
    @app.get("/empresas")
    def empresas():
        return render_template("empresas.html", empresas=db.listar(conn(), "empresas"))

    def _form_empresa(dados, erros, titulo, acao):
        campos = [F.Campo(**{**cp.__dict__, "opcoes": certificados_opcoes()}) if cp.nome == "certificado_id" else cp
                  for cp in F.EMPRESA]
        return render_template("form.html", campos=campos, dados=dados, erros=erros, titulo=titulo, acao=acao,
                               busca_cnpj="cnpj", busca_cep=True)

    @app.route("/empresas/nova", methods=["GET", "POST"])
    def empresa_nova():
        c = conn()
        if request.method == "POST":
            d, erros = F.validar_empresa(request.form)
            if not erros and c.execute("select 1 from empresas where cnpj = ?", (d["cnpj"],)).fetchone():
                erros["cnpj"] = "Já existe uma empresa com este CNPJ."
            if not erros:
                eid = db.inserir(c, "empresas", d)
                flash("Empresa cadastrada. Agora cadastre os clientes e os serviços dela.", "ok")
                return redirect(url_for("empresa", eid=eid))
            return _form_empresa(request.form, erros, "Nova empresa", url_for("empresa_nova"))
        dados = {cp.nome: cp.padrao for cp in F.EMPRESA}
        cid = request.args.get("certificado")
        if cid and (ct := db.obter(c, "certificados", int(cid))):
            dados.update(cnpj=formatar_documento(ct["documento"]), certificado_id=str(ct["id"]),
                         razao_social=(ct["titular"] or "").split(":")[0])
        return _form_empresa(dados, {}, "Nova empresa", url_for("empresa_nova"))

    @app.route("/empresas/<int:eid>/editar", methods=["GET", "POST"])
    def empresa_editar(eid):
        c = conn()
        emp = db.obter(c, "empresas", eid) or abort(404)
        if request.method == "POST":
            d, erros = F.validar_empresa(request.form)
            if not erros and d["cnpj"] != emp["cnpj"] and c.execute("select 1 from emissoes where empresa_id = ?", (eid,)).fetchone():
                erros["cnpj"] = "Esta empresa já tem notas. Para outro CNPJ, cadastre outra empresa."
            if not erros:
                db.atualizar(c, "empresas", eid, d)
                flash("Empresa atualizada.", "ok")
                return redirect(url_for("empresa", eid=eid))
            return _form_empresa(request.form, erros, f"Editar {emp['apelido']}", url_for("empresa_editar", eid=eid))
        dados = {k: ("" if v is None else str(v)) for k, v in emp.items()}
        dados["cnpj"] = formatar_documento(emp["cnpj"])
        return _form_empresa(dados, {}, f"Editar {emp['apelido']}", url_for("empresa_editar", eid=eid))

    @app.get("/empresas/<int:eid>")
    def empresa(eid):
        c = conn()
        emp = db.obter(c, "empresas", eid) or abort(404)
        modelos = c.execute("select m.*, cl.razao_social cliente, s.nome servico from modelos m join clientes cl "
                            "on cl.id = m.cliente_id join servicos s on s.id = m.servico_id where m.empresa_id = ? "
                            "order by m.id", (eid,)).fetchall()
        num = {amb: emissao.proximo_numero(c, eid, amb, emp["serie_dps"]) for amb in (C.PRODUCAO, C.HOMOLOGACAO)}
        return render_template("empresa.html", emp=emp, cert=db.obter(c, "certificados", emp["certificado_id"]) if emp["certificado_id"] else None,
                               clientes=db.listar(c, "clientes", empresa_id=eid), servicos=db.listar(c, "servicos", empresa_id=eid),
                               modelos=modelos, numeracao=num, marca=danfse.marca_efetiva(db.de_json(emp["marca_json"])))

    @app.post("/empresas/<int:eid>/numeracao")
    def empresa_numeracao(eid):
        c = conn()
        emp = db.obter(c, "empresas", eid) or abort(404)
        try:
            prox = int(request.form.get("proximo") or "0")
        except ValueError:
            prox = 0
        amb = request.form.get("ambiente") or C.PRODUCAO
        if prox < 1:
            flash("Número inválido.", "erro")
            return redirect(url_for("empresa", eid=eid))
        atual = emissao.proximo_numero(c, eid, amb, emp["serie_dps"])
        if prox < atual and not request.form.get("confirmo"):
            flash(f"Voltar a numeração de {atual} para {prox} pode repetir uma DPS. Marque a confirmação se tem certeza.", "erro")
        else:
            try:
                emissao.definir_proximo_numero(c, eid, amb, emp["serie_dps"], prox)
                flash(f"Próxima DPS ({C.nome_ambiente(amb)}): {prox}.", "ok")
            except ValueError as exc:
                flash(str(exc), "erro")
        return redirect(url_for("empresa", eid=eid))

    @app.route("/empresas/<int:eid>/marca", methods=["GET", "POST"])
    def empresa_marca(eid):
        c = conn()
        emp = db.obter(c, "empresas", eid) or abort(404)
        atual = db.de_json(emp["marca_json"], {}) or {}
        if request.method == "POST":
            if request.form.get("restaurar"):
                db.atualizar(c, "empresas", eid, {"marca_json": None})
                flash("Marca padrão (TechZyon) restaurada.", "ok")
                return redirect(url_for("empresa", eid=eid))
            m = F.validar_marca(request.form)
            logo = request.files.get("logo")
            if logo and logo.filename:
                ext = Path(logo.filename).suffix.lower()
                if ext not in (".png", ".jpg", ".jpeg"):
                    flash("O logo precisa ser PNG ou JPG.", "erro")
                    return redirect(url_for("empresa_marca", eid=eid))
                destino = C.dir_dados("marcas") / f"empresa-{eid}{ext}"
                logo.save(destino)
                m["logo"] = str(destino)
            elif atual.get("logo"):
                m["logo"] = atual["logo"]
            db.atualizar(c, "empresas", eid, {"marca_json": F.marca_para_json(m)})
            flash("Marca salva. Gere a prévia do PDF para conferir.", "ok")
            return redirect(url_for("empresa", eid=eid))
        dados = {cp.nome: cp.padrao for cp in F.MARCA}
        dados.update({k: ("1" if v is True else "" if v is False else v) for k, v in atual.items()})
        return render_template("form.html", campos=F.MARCA, dados=dados, erros={}, titulo=f"Marca do PDF: {emp['apelido']}",
                               acao=url_for("empresa_marca", eid=eid), multipart=True, restaurar=True)

    @app.get("/empresas/<int:eid>/previa-pdf")
    def empresa_previa_pdf(eid):
        emp = db.obter(conn(), "empresas", eid) or abort(404)
        arq = exemplo.gerar(C.dir_dados("exemplos", f"empresa-{eid}"), db.de_json(emp["marca_json"]))
        return send_file(arq, mimetype="application/pdf")

    @app.get("/empresas/<int:eid>/exportar")
    def empresa_exportar(eid):
        perfil = perfis.exportar(conn(), eid)
        nome = f"perfil-{limpar(perfil['empresa']['cnpj'])}.json"
        return Response(json.dumps(perfil, ensure_ascii=False, indent=2), mimetype="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{nome}"'})

    @app.post("/importar")
    def importar_perfil():
        arq = request.files.get("perfil")
        try:
            perfil = json.loads(arq.read().decode("utf-8")) if arq and arq.filename else None
            if not perfil:
                raise ValueError("Escolha o arquivo .json do perfil.")
            eid = perfis.importar(conn(), perfil)
            flash("Perfil importado. Ligue o certificado da empresa em Editar.", "ok")
            return redirect(url_for("empresa", eid=eid))
        except (ValueError, KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            flash(f"Não deu para importar: {exc}", "erro")
            return redirect(url_for("empresas"))

    # --- clientes, serviços, modelos (CRUD genérico por empresa) ---------------------------
    CADASTROS = {
        "clientes": ("cliente", F.CLIENTE, F.validar_cliente),
        "servicos": ("serviço", F.SERVICO, F.validar_servico),
        "modelos": ("modelo", F.MODELO, F.validar_modelo),
    }

    def _campos(tabela, eid):
        campos = CADASTROS[tabela][1]
        if tabela != "modelos":
            return campos
        cli = [(str(x["id"]), f"{x['razao_social']} ({formatar_documento(x['documento'])})")
               for x in db.listar(conn(), "clientes", empresa_id=eid, ativo=1)]
        srv = [(str(x["id"]), x["nome"]) for x in db.listar(conn(), "servicos", empresa_id=eid, ativo=1)]
        return [F.Campo(**{**cp.__dict__, "opcoes": cli if cp.nome == "cliente_id" else srv})
                if cp.nome in ("cliente_id", "servico_id") else cp for cp in campos]

    def _salvar(tabela, eid, reg_id=None):
        c = conn()
        nome, _campos_def, validar = CADASTROS[tabela]
        emp = db.obter(c, "empresas", eid) or abort(404)
        titulo = f"{'Editar' if reg_id else 'Novo'} {nome}: {emp['apelido']}"
        acao = request.path
        if request.method == "POST":
            d, erros = validar(request.form)
            if tabela == "modelos" and not erros:
                for k, t in (("cliente_id", "clientes"), ("servico_id", "servicos")):
                    r = db.obter(c, t, d[k])
                    if not r or r["empresa_id"] != eid:
                        erros[k] = "Escolha um desta empresa."
            if not erros:
                try:
                    if reg_id:
                        db.atualizar(c, tabela, reg_id, d)
                    else:
                        db.inserir(c, tabela, {**d, "empresa_id": eid})
                    flash(f"{nome.capitalize()} salvo.", "ok")
                    return redirect(url_for("empresa", eid=eid) + f"#{tabela}")
                except db.sqlite3.IntegrityError:
                    erros["_geral"] = "Já existe um cadastro igual nesta empresa (mesmo documento ou mesmo nome)."
            return render_template("form.html", campos=_campos(tabela, eid), dados=request.form, erros=erros,
                                   titulo=titulo, acao=acao, busca_cnpj="documento" if tabela == "clientes" else None,
                                   busca_cep=tabela == "clientes")
        dados = {cp.nome: cp.padrao for cp in CADASTROS[tabela][1]}
        if reg_id:
            reg = db.obter(c, tabela, reg_id)
            if not reg or reg["empresa_id"] != eid:
                abort(404)
            dados = {k: ("" if v is None else str(v)) for k, v in reg.items()}
            if tabela == "clientes":
                dados["documento"] = formatar_documento(reg["documento"])
        return render_template("form.html", campos=_campos(tabela, eid), dados=dados, erros={}, titulo=titulo,
                               acao=acao, busca_cnpj="documento" if tabela == "clientes" else None,
                               busca_cep=tabela == "clientes")

    @app.route("/empresas/<int:eid>/<tabela>/novo", methods=["GET", "POST"])
    def cadastro_novo(eid, tabela):
        if tabela not in CADASTROS:
            abort(404)
        return _salvar(tabela, eid)

    @app.route("/empresas/<int:eid>/<tabela>/<int:rid>", methods=["GET", "POST"])
    def cadastro_editar(eid, tabela, rid):
        if tabela not in CADASTROS:
            abort(404)
        return _salvar(tabela, eid, rid)

    @app.post("/empresas/<int:eid>/<tabela>/<int:rid>/ativo")
    def cadastro_ativo(eid, tabela, rid):
        if tabela not in CADASTROS:
            abort(404)
        reg = db.obter(conn(), tabela, rid)
        if not reg or reg["empresa_id"] != eid:
            abort(404)
        db.atualizar(conn(), tabela, rid, {"ativo": 0 if reg["ativo"] else 1})
        flash("Cadastro " + ("inativado." if reg["ativo"] else "reativado."), "ok")
        return redirect(url_for("empresa", eid=eid) + f"#{tabela}")

    # --- buscas auxiliares (só quando você clica no botão) ---------------------------------
    @app.get("/api/cnpj/<cnpj>")
    def api_cnpj(cnpj):
        try:
            r = requests.get(f"https://brasilapi.com.br/api/cnpj/v1/{limpar(cnpj)}", timeout=15)
            if r.status_code != 200:
                return jsonify(erro="CNPJ não encontrado na BrasilAPI."), 404
            j = r.json()
            return jsonify(razao_social=j.get("razao_social"), nome_fantasia=j.get("nome_fantasia"),
                           cep=so_digitos(j.get("cep")), logradouro=" ".join(x for x in [j.get("descricao_tipo_de_logradouro"), j.get("logradouro")] if x),
                           numero=j.get("numero"), complemento=j.get("complemento"), bairro=j.get("bairro"),
                           municipio=j.get("municipio"), uf=j.get("uf"),
                           cod_municipio=str(j.get("codigo_municipio_ibge") or ""),
                           email=(j.get("email") or "").lower() or None, telefone=so_digitos(j.get("ddd_telefone_1")))
        except requests.RequestException:
            return jsonify(erro="Sem conexão com a BrasilAPI agora. Preencha à mão."), 502

    @app.get("/api/cep/<cep>")
    def api_cep(cep):
        try:
            r = requests.get(f"https://viacep.com.br/ws/{so_digitos(cep)}/json/", timeout=15)
            j = r.json() if r.status_code == 200 else {}
            if not j or j.get("erro"):
                return jsonify(erro="CEP não encontrado."), 404
            return jsonify(logradouro=j.get("logradouro"), bairro=j.get("bairro"), municipio=j.get("localidade"),
                           uf=j.get("uf"), cod_municipio=j.get("ibge"))
        except (requests.RequestException, ValueError):
            return jsonify(erro="Sem conexão com o ViaCEP agora. Preencha à mão."), 502

    # --- emitir -----------------------------------------------------------------------------
    def _pedido_do_form(f) -> emissao.Pedido:
        mes = f.get("mes_referencia") or None
        pag = f.get("data_pagamento") or None
        comp = f.get("competencia") or None
        return emissao.Pedido(
            empresa_id=int(f["empresa_id"]), cliente_id=int(f["cliente_id"]), servico_id=int(f["servico_id"]),
            valor=f.get("valor") or None, descricao=f.get("descricao") or None,
            ambiente=f.get("ambiente") or C.HOMOLOGACAO, modelo_id=int(f["modelo_id"]) if f.get("modelo_id") else None,
            mes_referencia=mes, data_pagamento=date.fromisoformat(pag) if pag else None,
            competencia=date.fromisoformat(comp) if comp else None,
            certificado_id=int(f["certificado_id"]) if f.get("certificado_id") else None)

    @app.get("/emitir")
    def emitir():
        c = conn()
        emps = empresas_ativas()
        eid = request.args.get("empresa", type=int) or (emps[0]["id"] if len(emps) == 1 else None)
        emp = db.obter(c, "empresas", eid) if eid else None
        ctx = {"empresas": emps, "emp": emp, "certs": db.listar(c, "certificados")}
        if emp:
            ctx.update(clientes=db.listar(c, "clientes", empresa_id=eid, ativo=1),
                       servicos=db.listar(c, "servicos", empresa_id=eid, ativo=1),
                       modelos=db.listar(c, "modelos", empresa_id=eid, ativo=1))
            mid = request.args.get("modelo", type=int)
            mod = db.obter(c, "modelos", mid) if mid else None
            hoje = date.today()
            mes_ant = (hoje.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
            ctx["form"] = {
                "modelo_id": str(mod["id"]) if mod else "", "cliente_id": str(mod["cliente_id"]) if mod else "",
                "servico_id": str(mod["servico_id"]) if mod else "", "valor": mod["valor"] if mod else "",
                "mes_referencia": mes_ant, "data_pagamento": hoje.isoformat(), "descricao": "",
                "certificado_id": str(emp["certificado_id"] or ""), "ambiente": C.HOMOLOGACAO}
        return render_template("emitir.html", **ctx)

    @app.post("/emitir/previa")
    def emitir_previa():
        try:
            p = _pedido_do_form(request.form)
            prev = emissao.preparar(conn(), p, permitir_repetida=bool(request.form.get("permitir_repetida")),
                                    forcar_valor=bool(request.form.get("forcar_valor")))
        except (emissao.EmissaoErro, ValueError, KeyError) as exc:
            flash(f"Não deu para montar a prévia: {exc}", "erro")
            return redirect(url_for("emitir", empresa=request.form.get("empresa_id")))
        return render_template("previa.html", prev=prev, form=request.form)

    @app.post("/emitir/confirmar")
    def emitir_confirmar():
        f = request.form
        p = _pedido_do_form(f)
        if p.ambiente == C.PRODUCAO and (f.get("confirmacao") or "").strip().upper() != "EMITIR":
            flash("Para emitir em produção, digite EMITIR no campo de confirmação.", "erro")
            return emitir_previa()
        try:
            e = emissao.emitir(conn(), p, permitir_repetida=bool(f.get("permitir_repetida")),
                               forcar_valor=bool(f.get("forcar_valor")), sefin_factory=app.config["SEFIN_FACTORY"])
        except emissao.EmissaoErro as exc:
            flash("Emissão bloqueada: " + " | ".join(exc.problemas), "erro")
            return emitir_previa()
        except CERT.CertificadoErro as exc:
            flash(str(exc), "erro")
            return emitir_previa()
        return redirect(url_for("nota", nid=e["id"]))

    # --- notas ------------------------------------------------------------------------------
    @app.get("/notas")
    def notas():
        c = conn()
        eid = request.args.get("empresa", type=int)
        sql = ("select e.*, em.apelido empresa, cl.razao_social cliente from emissoes e join empresas em on "
               "em.id = e.empresa_id left join clientes cl on cl.id = e.cliente_id")
        args = ()
        if eid:
            sql += " where e.empresa_id = ?"
            args = (eid,)
        rows = c.execute(sql + " order by e.id desc limit 500", args).fetchall()
        return render_template("notas.html", notas=rows, empresas=db.listar(c, "empresas"), eid=eid,
                               pendentes={x["id"] for x in emissao.pendentes(c)})

    @app.get("/notas/<int:nid>")
    def nota(nid):
        e = db.obter(conn(), "emissoes", nid) or abort(404)
        snap = db.de_json(e["snapshot_json"], {})
        return render_template("nota.html", e=e, snap=snap, mensagens=db.de_json(e["mensagens_json"], []),
                               pasta=str(C.resolver(e["xml_path"]).parent) if e["xml_path"] else "",
                               pendente=e["id"] in {x["id"] for x in emissao.pendentes(conn())})

    @app.get("/notas/<int:nid>/<tipo>")
    def nota_arquivo(nid, tipo):
        e = db.obter(conn(), "emissoes", nid) or abort(404)
        caminho = e.get(f"{tipo}_path") if tipo in ("xml", "pdf") else None
        caminho = C.resolver(caminho) if caminho else None
        if not caminho or not caminho.exists():
            abort(404)
        return send_file(caminho, as_attachment=tipo == "xml", download_name=Path(caminho).name)

    @app.post("/notas/<int:nid>/verificar")
    def nota_verificar(nid):
        try:
            e = emissao.verificar(conn(), nid, sefin_factory=app.config["SEFIN_FACTORY"])
            flash(f"Conferido com a Sefin: {e['status']}.", "ok" if e["status"] == "emitida" else "aviso")
        except (emissao.EmissaoErro, CERT.CertificadoErro) as exc:
            flash(str(exc), "erro")
        return redirect(url_for("nota", nid=nid))

    @app.get("/exemplo.pdf")
    def exemplo_pdf():
        return send_file(exemplo.gerar(), mimetype="application/pdf")

    return app


def rodar(porta: int = 8765, abrir: bool = True) -> None:
    app = criar_app()
    url = f"http://127.0.0.1:{porta}/"
    print(f"\n  {NOME} v{__version__}\n  Painel em {url}  (só neste computador)\n  Para fechar: Ctrl+C\n")
    if abrir:
        import threading
        import webbrowser
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=porta, debug=False, use_reloader=False, threaded=True)
