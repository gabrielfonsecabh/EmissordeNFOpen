# Instruções para assistentes de IA

Este arquivo é para a IA (Claude, ChatGPT, Codex, Gemini, Copilot, Cursor) que está ajudando alguém a instalar, usar ou modificar o **Emissor de NF Open Source**, feito pela TechZyon. Siga estas regras. Elas existem porque um erro aqui vira uma nota fiscal errada, e nota fiscal não se desfaz com Ctrl+Z.

## Quem você provavelmente está ajudando

Uma pessoa **leiga** em tecnologia: dono de pequena empresa, MEI ou alguém de um escritório de contabilidade. Fale em português simples, um passo de cada vez, e espere a pessoa confirmar. Não despeje dez comandos de uma vez. Quando ela colar uma mensagem de erro, explique o que significa antes de mandar o próximo comando.

## Instalar

Siga [docs/01-instalar.md](docs/01-instalar.md). Resumo técnico:

- O projeto usa **uv** (Astral) para Python e dependências. Os instaladores (`instalar.sh`, `instalar.ps1`, `Instalar no Mac.command`, `Instalar no Windows.bat`) instalam o uv se faltar, rodam `uv sync`, os testes e geram um PDF de exemplo.
- Python 3.11 ou mais novo. O uv baixa o Python sozinho se precisar. Não peça para a pessoa instalar Python à parte.
- Abrir: `uv run emissor painel` (ou os atalhos `Abrir Emissor.command`, `Abrir Emissor.bat`, `./emissor painel`). O painel fica em `http://127.0.0.1:8765` e só aceita conexões da própria máquina.
- Testes: `uv run pytest`. Todos precisam passar. Eles usam pasta temporária e não tocam nos dados da pessoa.

## Regras de segurança (obrigatórias)

1. **Nunca peça, leia, copie, imprima ou envie** a senha do certificado, o arquivo `.pfx`/`.p12` ou qualquer coisa dentro de `dados/`. A senha é digitada pela pessoa no painel e vai para o cofre do sistema operacional (keyring).
2. **Nunca emita em produção** (`--producao` ou ambiente "Produção" no painel) sem a pessoa pedir explicitamente para aquela nota específica. No painel, produção exige digitar `EMITIR`. Não contorne isso. Na linha de comando, não use `--sim` por conta própria.
3. **Comece sempre em homologação.** A primeira nota de qualquer empresa nova é de teste.
4. **Não desligue travas** (`--permitir-repetida`, `--forcar-valor`, liberar duplicidade ou valor fora da faixa) sem a pessoa entender e pedir.
5. **Nota com status `verificar`:** não emita outra igual. Rode `emissor verificar` (ou o botão "Conferir com a Sefin"). O emissor consulta a Sefin pelo id da DPS antes de reenviar e nunca gera nota duplicada sozinho.
6. **Não faça commit de `dados/`** nem de certificados. Já estão no `.gitignore`. Se a pessoa for publicar um fork, confira com `git status` antes.

## Mapa do código

| Arquivo | O que faz |
|---|---|
| `emissor_nf/config.py` | Caminhos, URLs da Sefin, ambientes, data da NT 009 |
| `emissor_nf/db.py` | Banco SQLite local (`dados/emissor.db`) e o esquema de tabelas |
| `emissor_nf/certificados.py` | Importa A1, lê CNPJ/CPF do certificado, guarda a senha no keyring |
| `emissor_nf/dps.py` | Monta o XML da DPS nos leiautes v1.01 e NT 009 e valida contra o XSD oficial |
| `emissor_nf/assinatura.py` | Assinatura XMLDSig (RSA-SHA256, c14n exclusiva) |
| `emissor_nf/sefin.py` | Cliente HTTP mTLS da Sefin Nacional (emitir, consultar DPS, baixar NFS-e) |
| `emissor_nf/emissao.py` | Prévia, travas, numeração, envio, retomada segura e arquivos |
| `emissor_nf/danfse.py` | PDF (DANFSe) com marca personalizável e linha de créditos |
| `emissor_nf/perfis.py` | Exporta/importa cadastro de uma empresa (sem certificado nem senha) |
| `emissor_nf/painel/` | Painel web local (Flask), com CSRF e checagem de Host |
| `emissor_nf/__main__.py` | Comando `emissor` |
| `tests/` | Testes, incluindo comparação com uma nota real anonimizada aceita pela Sefin |

## Ao modificar o código

- Rode `uv run pytest` antes e depois. Não apague nem afrouxe teste para ele passar.
- Mudou o XML da DPS? O teste `test_dps_identica_a_nota_real_aceita_pela_sefin` e a validação XSD precisam continuar passando nos dois leiautes.
- Não remova a linha de créditos padrão, os arquivos `LICENSE` e `NOTICE` nem o rodapé "Feito pela TechZyon" do painel. Personalização de marca é por empresa, pelo painel. Veja [CREDITOS-E-MARCA.md](CREDITOS-E-MARCA.md).
- Não adicione telemetria, envio de dados para servidores próprios nem dependência de nuvem. O projeto é 100% local por princípio.
- Texto para o usuário em português do Brasil, simples e direto.

## Limites atuais (o emissor bloqueia, não tente contornar)

Não optante do Simples, ISS retido, tomador estrangeiro, intermediário, obra, evento, cancelamento/substituição, certificado A3, municípios fora do padrão nacional, IBS/CBS.
