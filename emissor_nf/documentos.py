"""Validação e formatação de CNPJ (inclusive alfanumérico), CPF, CEP e telefone."""

from __future__ import annotations

import re


def limpar(texto: str | None) -> str:
    """Tira pontos, barras, traços e espaços; letras ficam maiúsculas (CNPJ alfanumérico)."""
    return re.sub(r"[^0-9A-Za-z]", "", texto or "").upper()


def so_digitos(texto: str | None) -> str:
    return re.sub(r"\D", "", texto or "")


def _dv_cnpj(base: str) -> str:
    # Regra da Receita para o CNPJ alfanumérico: cada caractere vale (código ASCII - 48),
    # o que mantém o cálculo antigo para os dígitos 0 a 9.
    def dv(parcial: str) -> int:
        pesos = list(range(len(parcial) - 7, 1, -1)) + list(range(9, 1, -1))
        soma = sum((ord(c) - 48) * p for c, p in zip(parcial, pesos))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    d1 = dv(base)
    d2 = dv(base + str(d1))
    return f"{d1}{d2}"


def cnpj_valido(cnpj: str | None) -> bool:
    c = limpar(cnpj)
    if not re.fullmatch(r"[0-9A-Z]{12}[0-9]{2}", c):
        return False
    if len(set(c)) == 1:
        return False
    return c[12:] == _dv_cnpj(c[:12])


def cpf_valido(cpf: str | None) -> bool:
    c = so_digitos(cpf)
    if len(c) != 11 or len(set(c)) == 1:
        return False
    for n in (9, 10):
        soma = sum(int(c[i]) * (n + 1 - i) for i in range(n))
        dv = (soma * 10) % 11 % 10
        if dv != int(c[n]):
            return False
    return True


def tipo_documento(doc: str | None) -> str | None:
    d = limpar(doc)
    if len(d) == 14 and cnpj_valido(d):
        return "CNPJ"
    if len(d) == 11 and cpf_valido(d):
        return "CPF"
    return None


def formatar_documento(doc: str | None) -> str:
    d = limpar(doc)
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return doc or ""


def formatar_cep(cep: str | None) -> str:
    c = so_digitos(cep)
    return f"{c[:5]}-{c[5:]}" if len(c) == 8 else (cep or "")


def formatar_telefone(fone: str | None) -> str:
    f = so_digitos(fone)
    if len(f) == 10:
        return f"({f[:2]}) {f[2:6]}-{f[6:]}"
    if len(f) == 11:
        return f"({f[:2]}) {f[2:7]}-{f[7:]}"
    return fone or ""


def gerar_cnpj_ficticio(base12: str) -> str:
    """Só para testes e exemplos: completa 12 caracteres com os dígitos verificadores."""
    b = limpar(base12)[:12]
    return b + _dv_cnpj(b)
