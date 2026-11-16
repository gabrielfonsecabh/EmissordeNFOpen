"""Campos e validação dos cadastros (usados pelo painel e pela linha de comando).

Cada campo: nome, rótulo, tipo, obrigatório, ajuda (texto que aparece embaixo do campo).
A validação devolve (dados_limpos, erros); erros é um dicionário campo -> mensagem.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .documentos import cnpj_valido, cpf_valido, limpar, so_digitos
from .emissao import valor_decimal

UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
       "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]


@dataclass
class Campo:
    nome: str
    rotulo: str
    tipo: str = "text"            # text, textarea, select, number, email, password, file, checkbox, color
    obrigatorio: bool = False
    ajuda: str = ""
    opcoes: list[tuple[str, str]] = field(default_factory=list)
    padrao: str = ""
    grupo: str = ""


EMPRESA = [
    Campo("apelido", "Apelido (como você chama esta empresa)", obrigatorio=True, grupo="Identificação",
          ajuda="Só para você achar fácil na lista. Ex.: Minha empresa, Cliente Padaria."),
    Campo("cnpj", "CNPJ", obrigatorio=True, grupo="Identificação",
          ajuda="Com ou sem pontuação. Aceita o CNPJ novo com letras. Use o botão para buscar os dados."),
    Campo("razao_social", "Razão social", obrigatorio=True, grupo="Identificação"),
    Campo("nome_fantasia", "Nome fantasia", grupo="Identificação"),
    Campo("inscricao_municipal", "Inscrição municipal", grupo="Identificação",
          ajuda="Está no alvará ou no cadastro da prefeitura. Deixe vazio se o município não exige."),
    Campo("cep", "CEP", obrigatorio=True, grupo="Endereço", ajuda="Use o botão para preencher o endereço e o código do município."),
    Campo("logradouro", "Rua / avenida", grupo="Endereço"),
    Campo("numero", "Número", grupo="Endereço"),
    Campo("complemento", "Complemento", grupo="Endereço"),
    Campo("bairro", "Bairro", grupo="Endereço"),
    Campo("municipio", "Município", obrigatorio=True, grupo="Endereço"),
    Campo("uf", "UF", "select", True, opcoes=[(u, u) for u in UFS], grupo="Endereço"),
    Campo("cod_municipio", "Código IBGE do município", obrigatorio=True, grupo="Endereço",
          ajuda="7 dígitos. Ex.: São Paulo 3550308. A busca pelo CEP preenche sozinha."),
    Campo("telefone", "Telefone", grupo="Contato"),
    Campo("email", "E-mail", "email", grupo="Contato"),
    Campo("opcao_simples", "Regime", "select", True, grupo="Tributação", padrao="3", opcoes=[
        ("3", "Simples Nacional: ME ou EPP"), ("2", "Simples Nacional: MEI"),
        ("1", "Não optante do Simples (ainda não suportado)")]),
    Campo("regime_apuracao_simples", "Apuração do Simples (ME/EPP)", "select", grupo="Tributação", padrao="1", opcoes=[
        ("1", "Tributos federais e municipal pelo Simples (o normal)"),
        ("2", "Federais pelo Simples e ISS por fora"), ("3", "Federais e ISS por fora")],
          ajuda="Na dúvida, pergunte ao seu contador. Quase sempre é a primeira opção."),
    Campo("regime_especial", "Regime especial de tributação", "select", grupo="Tributação", padrao="0", opcoes=[
        ("0", "Nenhum"), ("1", "Ato cooperado"), ("2", "Estimativa"), ("3", "Microempresa municipal"),
        ("4", "Notário ou registrador"), ("5", "Profissional autônomo"), ("6", "Sociedade de profissionais")]),
    Campo("serie_dps", "Série da DPS", "number", True, padrao="1", grupo="Tributação",
          ajuda="Deixe 1. Só mude se você já emite por outro sistema próprio com a série 1."),
    Campo("certificado_id", "Certificado padrão", "select", grupo="Certificado",
          ajuda="O certificado A1 desta empresa. Dá para trocar na hora de emitir."),
    Campo("pasta_saida", "Pasta onde salvar as notas (opcional)", grupo="Arquivos",
          ajuda="Caminho completo de uma pasta do seu computador. Vazio = dados/notas/<CNPJ>/. "
                "As notas são separadas por ano e mês dentro dela."),
]

CLIENTE = [
    Campo("documento", "CNPJ ou CPF", obrigatorio=True, ajuda="Com ou sem pontuação. Use o botão para buscar os dados do CNPJ."),
    Campo("razao_social", "Nome / razão social", obrigatorio=True),
    Campo("email", "E-mail", "email"),
    Campo("telefone", "Telefone"),
    Campo("cep", "CEP", obrigatorio=True, ajuda="Use o botão para preencher o endereço e o código do município."),
    Campo("logradouro", "Rua / avenida", obrigatorio=True),
    Campo("numero", "Número", obrigatorio=True, ajuda="Sem número? Escreva S/N."),
    Campo("complemento", "Complemento"),
    Campo("bairro", "Bairro", obrigatorio=True),
    Campo("municipio", "Município"),
    Campo("uf", "UF", "select", opcoes=[("", "-")] + [(u, u) for u in UFS]),
    Campo("cod_municipio", "Código IBGE do município", obrigatorio=True, ajuda="7 dígitos. A busca pelo CEP preenche sozinha."),
]

SERVICO = [
    Campo("nome", "Nome do serviço", obrigatorio=True, ajuda="Para você reconhecer. Ex.: Consultoria mensal."),
    Campo("cod_trib_nacional", "Código de tributação nacional", obrigatorio=True,
          ajuda="6 dígitos, da lista nacional de serviços (item + subitem + desdobramento). Ex.: 010101 (análise e desenvolvimento de sistemas). "
                "Veja docs/03-cadastros-e-codigos.md para achar o seu."),
    Campo("cod_trib_municipal", "Código de tributação municipal",
          ajuda="3 dígitos, só se a sua prefeitura usa. Na dúvida, deixe vazio."),
    Campo("cod_nbs", "Código NBS", ajuda="9 dígitos (Nomenclatura Brasileira de Serviços). Opcional por enquanto."),
    Campo("perc_trib_sn", "Tributos aproximados do Simples (%)", "text", padrao="6.00",
          ajuda="Obrigatório para ME/EPP: a alíquota efetiva aproximada do Simples (ex.: 6,00). Seu contador sabe."),
    Campo("descricao_padrao", "Descrição padrão", "textarea",
          ajuda="Texto que vai na nota. Pode usar {mes_ref}, {ano_ref}, {mes_num} e {data_pagamento}."),
    Campo("valor_padrao", "Valor padrão (R$)"),
    Campo("cod_local_prestacao", "Código IBGE do local da prestação",
          ajuda="Vazio = município do cliente. Preencha se o serviço é prestado em outro lugar."),
    Campo("trib_issqn", "Tributação do ISS", "select", padrao="1", opcoes=[
        ("1", "Operação tributável (o normal)"), ("2", "Imunidade"), ("3", "Exportação de serviço"),
        ("4", "Não incidência")]),
    Campo("cst_pis_cofins", "CST de PIS/Cofins (opcional)",
          ajuda="Só se o seu contador pediu. Ex.: 07. Vazio = não informa PIS/Cofins na nota."),
    Campo("tp_ret_pis_cofins", "Retenção de PIS/Cofins", "select", padrao="0", opcoes=[
        ("0", "Não retidos"), ("1", "PIS/Cofins retidos"), ("2", "PIS/Cofins não retidos")]),
]

MODELO = [
    Campo("nome", "Nome do modelo", obrigatorio=True, ajuda="Ex.: Mensalidade Cliente X."),
    Campo("cliente_id", "Cliente", "select", True),
    Campo("servico_id", "Serviço", "select", True),
    Campo("valor", "Valor (R$)", obrigatorio=True),
    Campo("valor_minimo", "Valor mínimo aceito (R$)", ajuda="Trava contra erro de digitação. Opcional."),
    Campo("valor_maximo", "Valor máximo aceito (R$)", ajuda="Trava contra erro de digitação. Opcional."),
    Campo("descricao_modelo", "Texto da nota", "textarea", True,
          ajuda="Pode usar {mes_ref} (Janeiro), {ano_ref} (2027), {mes_num} (01) e {data_pagamento}."),
]

MARCA = [
    Campo("nome", "Nome que aparece no topo do PDF", ajuda="Vazio = marca padrão TechZyon."),
    Campo("subtitulo", "Subtítulo"),
    Campo("slogan", "Slogan (rodapé)"),
    Campo("site", "Site (rodapé)"),
    Campo("contato", "Contato (rodapé)", ajuda="Telefone ou e-mail."),
    Campo("cor_acento", "Cor de destaque", "color", padrao="#1d4ed8"),
    Campo("cor_texto", "Cor do texto", "color", padrao="#101010"),
    Campo("logo", "Logo (PNG ou JPG, quadrado de preferência)", "file"),
    Campo("creditos", "Manter a linha de créditos do projeto no rodapé", "checkbox", padrao="1",
          ajuda="Se você usa este emissor para fins comerciais, mantenha os créditos. Veja CREDITOS-E-MARCA.md."),
]


def _txt(form, nome) -> str:
    return (form.get(nome) or "").strip()


def validar_empresa(form) -> tuple[dict, dict]:
    erros, d = {}, {}
    for c in EMPRESA:
        d[c.nome] = _txt(form, c.nome) or None
    d["cnpj"] = limpar(d["cnpj"])
    if not cnpj_valido(d["cnpj"]):
        erros["cnpj"] = "CNPJ inválido (confira os dígitos)."
    d["cep"] = so_digitos(d["cep"]) or None
    if not d["cep"] or len(d["cep"]) != 8:
        erros["cep"] = "CEP precisa de 8 dígitos."
    d["cod_municipio"] = so_digitos(d["cod_municipio"])
    if len(d["cod_municipio"]) != 7:
        erros["cod_municipio"] = "Código IBGE precisa de 7 dígitos."
    if d["uf"] not in UFS:
        erros["uf"] = "Escolha a UF."
    d["inscricao_municipal"] = so_digitos(d["inscricao_municipal"]) or None
    d["telefone"] = so_digitos(d["telefone"]) or None
    try:
        d["serie_dps"] = int(d["serie_dps"] or 1)
        if not 1 <= d["serie_dps"] <= 49999:
            raise ValueError
    except ValueError:
        erros["serie_dps"] = "Série entre 1 e 49999."
    d["certificado_id"] = int(d["certificado_id"]) if d["certificado_id"] else None
    for obrig in ("apelido", "razao_social", "municipio"):
        if not d[obrig]:
            erros[obrig] = "Obrigatório."
    return d, erros


def validar_cliente(form) -> tuple[dict, dict]:
    erros, d = {}, {}
    for c in CLIENTE:
        d[c.nome] = _txt(form, c.nome) or None
    doc = limpar(d["documento"])
    if len(doc) == 11 and cpf_valido(doc):
        d["tipo_doc"] = "CPF"
    elif len(doc) == 14 and cnpj_valido(doc):
        d["tipo_doc"] = "CNPJ"
    else:
        erros["documento"] = "CNPJ ou CPF inválido (confira os dígitos)."
    d["documento"] = doc
    d["cep"] = so_digitos(d["cep"])
    if len(d["cep"] or "") != 8:
        erros["cep"] = "CEP precisa de 8 dígitos."
    d["cod_municipio"] = so_digitos(d["cod_municipio"])
    if len(d["cod_municipio"] or "") != 7:
        erros["cod_municipio"] = "Código IBGE precisa de 7 dígitos."
    d["telefone"] = so_digitos(d["telefone"]) or None
    if d["telefone"] and not 6 <= len(d["telefone"]) <= 20:
        erros["telefone"] = "Telefone inválido."
    if d["email"] and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", d["email"]):
        erros["email"] = "E-mail inválido."
    for obrig in ("razao_social", "logradouro", "numero", "bairro"):
        if not d[obrig]:
            erros[obrig] = "Obrigatório."
    return d, erros


def validar_servico(form) -> tuple[dict, dict]:
    erros, d = {}, {}
    for c in SERVICO:
        d[c.nome] = _txt(form, c.nome) or None
    d["cod_trib_nacional"] = so_digitos(d["cod_trib_nacional"])
    if len(d["cod_trib_nacional"] or "") != 6:
        erros["cod_trib_nacional"] = "Código de tributação nacional precisa de 6 dígitos."
    d["cod_trib_municipal"] = so_digitos(d["cod_trib_municipal"]) or None
    if d["cod_trib_municipal"] and len(d["cod_trib_municipal"]) != 3:
        erros["cod_trib_municipal"] = "Código municipal tem 3 dígitos."
    d["cod_nbs"] = so_digitos(d["cod_nbs"]) or None
    if d["cod_nbs"] and len(d["cod_nbs"]) != 9:
        erros["cod_nbs"] = "NBS tem 9 dígitos."
    d["cod_local_prestacao"] = so_digitos(d["cod_local_prestacao"]) or None
    if d["cod_local_prestacao"] and len(d["cod_local_prestacao"]) != 7:
        erros["cod_local_prestacao"] = "Código IBGE tem 7 dígitos."
    if d["perc_trib_sn"]:
        p = valor_decimal(d["perc_trib_sn"])
        if p is None or not 0 <= p <= 100:
            erros["perc_trib_sn"] = "Percentual entre 0 e 100."
        else:
            d["perc_trib_sn"] = str(p)
    if d["valor_padrao"]:
        v = valor_decimal(d["valor_padrao"])
        if v is None or v <= 0:
            erros["valor_padrao"] = "Valor inválido."
        else:
            d["valor_padrao"] = str(v)
    d["cst_pis_cofins"] = so_digitos(d["cst_pis_cofins"]) or None
    if d["cst_pis_cofins"] and len(d["cst_pis_cofins"]) != 2:
        erros["cst_pis_cofins"] = "CST tem 2 dígitos."
    if not d["cst_pis_cofins"]:
        d["tp_ret_pis_cofins"] = None
    if not d["nome"]:
        erros["nome"] = "Obrigatório."
    return d, erros


def validar_modelo(form) -> tuple[dict, dict]:
    erros, d = {}, {}
    for c in MODELO:
        d[c.nome] = _txt(form, c.nome) or None
    for k in ("valor", "valor_minimo", "valor_maximo"):
        if d[k]:
            v = valor_decimal(d[k])
            if v is None or v <= 0:
                erros[k] = "Valor inválido."
            else:
                d[k] = str(v)
    if not d["valor"]:
        erros["valor"] = "Obrigatório."
    if not erros and d["valor_minimo"] and d["valor_maximo"]:
        if not valor_decimal(d["valor_minimo"]) <= valor_decimal(d["valor"]) <= valor_decimal(d["valor_maximo"]):
            erros["valor"] = "O valor precisa estar entre o mínimo e o máximo."
    for k in ("cliente_id", "servico_id"):
        try:
            d[k] = int(d[k])
        except (TypeError, ValueError):
            erros[k] = "Escolha um."
    for obrig in ("nome", "descricao_modelo"):
        if not d[obrig]:
            erros[obrig] = "Obrigatório."
    return d, erros


def validar_marca(form) -> dict:
    m = {}
    for c in MARCA:
        if c.tipo == "file":
            continue
        if c.tipo == "checkbox":
            m[c.nome] = bool(form.get(c.nome))
        else:
            v = _txt(form, c.nome)
            if c.tipo == "color" and not re.fullmatch(r"#[0-9a-fA-F]{6}", v or ""):
                v = c.padrao
            m[c.nome] = v
    return m


def marca_para_json(m: dict) -> str:
    return json.dumps(m, ensure_ascii=False)
