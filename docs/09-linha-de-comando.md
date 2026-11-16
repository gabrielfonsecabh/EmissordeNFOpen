# 9. Linha de comando

Tudo o que o painel faz também dá para fazer pelo terminal. Útil para automatizar (agendar a nota mensal, integrar com outro sistema) ou para quem prefere teclado.

Dentro da pasta do emissor:

- **Mac/Linux:** `./emissor <comando>`
- **Windows:** `emissor <comando>`
- **Qualquer sistema:** `uv run emissor <comando>`

## Comandos

```bash
emissor painel                    # abre o painel (--porta 8766, --sem-navegador)
emissor status                    # certificados, empresas, numeração e pendências
emissor exemplo                   # gera um PDF fictício de exemplo

emissor certificado adicionar caminho/cert.pfx --apelido "Minha empresa"   # pede a senha
emissor certificado listar
emissor certificado testar 1      # testa na homologação (--producao para testar na produção)
emissor certificado remover 1

emissor empresa listar
emissor empresa exportar <id|apelido|CNPJ> perfil.json
emissor importar perfil.json --certificado 1

emissor notas [--empresa X]       # lista as emissões
emissor verificar [id]            # confere com a Sefin as emissões pendentes
emissor pdf nota.xml [--empresa X]  # gera o PDF de novo a partir do XML
```

## Emitir

```bash
# Prévia apenas (não envia nada)
emissor emitir --empresa "Minha empresa" --modelo "Mensalidade" --mes-ref 10/2026 --so-previa

# Nota de TESTE (homologação é o padrão)
emissor emitir --empresa "Minha empresa" --modelo "Mensalidade" --mes-ref 10/2026 --pagamento 05/11/2026

# Nota de VERDADE: pede para digitar EMITIR
emissor emitir --empresa "Minha empresa" --modelo "Mensalidade" --mes-ref 10/2026 --producao
```

Sem modelo, informe cliente, serviço, valor e (se o serviço não tiver texto padrão) a descrição:

```bash
emissor emitir --empresa 1 --cliente 33.444.555/0001-81 --servico "Consultoria" \
  --valor 1500,00 --descricao "Consultoria de outubro/2026" --mes-ref 10/2026
```

| Opção | Para que serve |
|---|---|
| `--producao` | Emite de verdade. Sem ela, é teste. |
| `--certificado ID` | Usa outro certificado em vez do padrão da empresa. |
| `--competencia DD/MM/AAAA` | Data de competência (padrão: hoje). |
| `--sim` | Não pede para digitar EMITIR. **Use só em automação que você mesmo revisou.** |
| `--permitir-repetida` | Libera a trava de nota repetida para o mesmo cliente no mês. |
| `--forcar-valor` | Libera a trava de valor fora da faixa do modelo. |

## Automação sem cofre de senhas

Em servidor ou ambiente sem cofre (alguns Linux), defina a senha por variável de ambiente, só para o processo que emite:

```bash
EMISSOR_SENHA_CERT_1='senha-do-certificado' emissor emitir ...
```

Para guardar os dados em outro lugar (ex.: disco criptografado), use `EMISSOR_DADOS=/caminho/para/dados`.
