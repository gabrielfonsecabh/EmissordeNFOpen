# 3. Cadastros: empresa, clientes, serviços e modelos

A ideia é cadastrar tudo **uma vez**. Depois, emitir é escolher um modelo e conferir.

```
Empresa (quem emite)
 ├── Clientes (quem recebe a nota)
 ├── Serviços (o que você presta, com os códigos fiscais)
 └── Modelos (cliente + serviço + valor + texto prontos)
```

> **O atalho mais seguro:** abra o PDF ou o XML de uma nota que você já emitiu pelo portal nacional e que deu certo. Quase todos os códigos que o emissor pede estão nela. Copie de lá.

## Empresa

Painel → **Empresas** → **Nova empresa** (ou, na tela de certificados, **Criar empresa com ele**).

| Campo | O que colocar |
|---|---|
| Apelido | Um nome curto para você. Ex.: *Minha empresa*, *Cliente Padaria*. |
| CNPJ | Digite e clique em **Buscar dados do CNPJ**: razão social e endereço se preenchem sozinhos (consulta pública na BrasilAPI). |
| Inscrição municipal | Está no alvará ou no cadastro da prefeitura. Se o seu município não usa, deixe vazio. |
| CEP | Clique em **Buscar pelo CEP** para preencher endereço e **código IBGE do município**. |
| Regime | *Simples Nacional: ME ou EPP* ou *Simples Nacional: MEI*. |
| Apuração do Simples | Quase sempre a primeira opção. Na dúvida, pergunte ao contador. |
| Regime especial | Quase sempre *Nenhum*. |
| Série da DPS | Deixe **1**. Veja a explicação abaixo. |
| Certificado padrão | O certificado A1 desta empresa. |
| Pasta onde salvar as notas | Opcional. Ex.: `/Users/maria/Documentos/Notas` ou `C:\Users\Maria\Documents\Notas`. Vazio = dentro de `dados/notas/`. |

### Série e numeração (leia, é importante)

Toda nota tem uma **série** e um **número de DPS**. O portal nacional (Emissor Web) usa a série **70000**. Sistemas próprios como este usam séries de **1 a 49999**. Por isso as notas deste emissor nunca colidem com as que você faz no portal.

- Primeira vez usando um sistema próprio? Deixe série 1. A numeração começa em 1.
- Já emitia por **outro sistema próprio** com a série 1? Na página da empresa, em **Numeração**, informe o próximo número livre (o último usado + 1). Ou use outra série, como 2.

## Clientes (tomadores)

Página da empresa → **Novo cliente**.

- **CNPJ ou CPF**: com CNPJ, clique em **Buscar dados do CNPJ**.
- **CEP**: clique em **Buscar pelo CEP**. O código IBGE é obrigatório.
- **E-mail e telefone**: opcionais. Vão impressos na nota.

## Serviços

Página da empresa → **Novo serviço**. Aqui moram os códigos fiscais.

| Campo | O que é | Onde achar |
|---|---|---|
| Código de tributação nacional | 6 dígitos: item, subitem e desdobramento da lista nacional de serviços. Ex.: `010101` = análise e desenvolvimento de sistemas; `170202` = apoio administrativo. | Na sua última nota (campo "Código de Tributação Nacional"), no próprio portal nacional ao emitir (a lista aparece para escolher) ou com o contador. Pode digitar com ou sem pontos. |
| Código de tributação municipal | 3 dígitos, só em alguns municípios. | Na sua última nota. Se não aparece, deixe vazio. |
| Código NBS | 9 dígitos. Opcional por enquanto. | Na sua última nota ou com o contador. |
| Tributos aproximados do Simples (%) | A alíquota efetiva aproximada que você paga no Simples. **Obrigatório para ME/EPP.** Não usado para MEI. | Com o contador ou na sua última nota ("Valor aproximado dos tributos"). |
| Local da prestação | Código IBGE de onde o serviço é prestado. | Vazio = cidade do cliente. |
| Tributação do ISS | Quase sempre *Operação tributável*. | |
| CST de PIS/Cofins | Só se o contador pediu (ex.: `07`). | Vazio = não informa. |
| Descrição padrão | Texto da nota. Aceita variáveis (abaixo). | |

## Modelos de nota

Página da empresa → **Novo modelo**. Um modelo junta **cliente + serviço + valor + texto**. É o que você escolhe na hora de emitir.

| Campo | Dica |
|---|---|
| Nome | Ex.: *Mensalidade Padaria*. |
| Valor | Ex.: `1.500,00`. |
| Valor mínimo e máximo | Opcionais, mas recomendados. Se alguém digitar `15.000` em vez de `1.500`, o emissor trava. |
| Texto da nota | Ex.: `Consultoria referente a {mes_ref}/{ano_ref}. Vencimento em {data_pagamento}.` |

### Variáveis do texto

| Variável | Vira |
|---|---|
| `{mes_ref}` | Nome do mês de referência: *Outubro* |
| `{ano_ref}` | Ano de referência: *2026* |
| `{mes_num}` | Mês com dois dígitos: *10* |
| `{data_pagamento}` | Data de pagamento informada na emissão: *05/11/2026* |

Exemplo: o texto `Serviços de {mes_ref}/{ano_ref}, pagamento em {data_pagamento}`, emitido com referência outubro/2026 e pagamento 05/11/2026, vira **Serviços de Outubro/2026, pagamento em 05/11/2026**.

## Desativar em vez de apagar

Cliente, serviço ou modelo que não usa mais? Clique em **Desativar**. Ele some das listas de emissão, mas o histórico das notas continua intacto.

**Próximo passo:** [emitir a primeira nota](04-primeira-nota.md).
