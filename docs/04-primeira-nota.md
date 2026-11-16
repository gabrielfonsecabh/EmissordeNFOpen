# 4. Emitir a primeira nota

## Dois ambientes

| | Homologação (teste) | Produção (de verdade) |
|---|---|---|
| Vale como nota fiscal? | **Não**. Serve para treinar. | **Sim**. |
| Onde salva | `dados/homologacao/...`, arquivos com prefixo `HOMOLOGACAO_` | `dados/notas/...` ou a pasta da empresa |
| PDF | Com a marca d'água "SEM VALOR FISCAL" | Normal |
| Confirmação | Um clique | Digitar `EMITIR` |

O emissor começa **sempre em homologação**. Faça pelo menos uma nota de teste para cada empresa nova.

## Passo a passo

1. Painel → **Emitir**.
2. Escolha a **empresa** e clique em **Escolher**.
3. Escolha um **modelo**. Cliente, serviço, valor e texto se preenchem sozinhos. Pode ajustar qualquer campo só para esta nota.
4. Preencha:
   - **Mês de referência**: o mês a que o serviço se refere.
   - **Data de pagamento**: opcional, entra no texto se o modelo usar `{data_pagamento}`.
   - **Competência**: deixe vazio para usar hoje. Não pode ser data futura.
   - **Ambiente**: *Homologação* para teste.
5. Clique em **Ver a prévia**.
6. **Confira tudo** com calma: tomador, valor, texto, código do serviço. A prévia mostra:
   - **Bloqueios** (vermelho): impedem a emissão. Corrija e volte.
   - **Avisos** (amarelo): não impedem, mas leia.
7. Clique em **Emitir nota de teste**.
8. Em poucos segundos aparece **NFS-e nº ...** com os botões **Abrir PDF** e **Baixar XML**.

## Emitir de verdade

Repita os passos escolhendo **Produção**. Na prévia, digite `EMITIR` no campo de confirmação e clique em **Emitir nota**.

Depois:

- Confira o PDF.
- Mande o PDF (e o XML, se o cliente pedir) para o seu cliente.
- A nota também aparece no portal nacional (gov.br/nfse), no menu de notas emitidas.

## As travas de segurança

| Trava | O que acontece | Dá para liberar? |
|---|---|---|
| Nota para o mesmo cliente no mesmo mês de referência | Bloqueia em produção | Sim, na prévia, se for intencional |
| Valor fora da faixa do modelo | Bloqueia | Sim, na prévia, depois de conferir |
| Certificado vencido ou de outro CNPJ | Bloqueia | Não. Troque o certificado. |
| Competência no futuro, valor zerado, descrição vazia | Bloqueia | Não. Corrija. |
| Situação não suportada (ISS retido, não optante...) | Bloqueia | Não. Use o portal nacional. |

## Se a internet cair no meio

O emissor reserva o número da nota **antes** de enviar e, se não tiver certeza do resultado, marca a emissão como **verificar**. Ela aparece em destaque na tela inicial.

Abra a nota e clique em **Conferir com a Sefin**. O emissor pergunta à Sefin se aquele número já virou nota:

- Se virou, baixa a nota e salva os arquivos. **Não emite de novo.**
- Se não virou, envia de novo com o **mesmo número**, o que impede nota em dobro.

**Nunca emita outra nota igual enquanto houver uma "verificar" pendente.** Confira primeiro.

## Se a Sefin recusar

A nota fica como **rejeitada** e a tela mostra o motivo com o código do erro (ex.: `E0312`). Nada foi emitido. Corrija o cadastro (veja [07-problemas-comuns.md](07-problemas-comuns.md)) e emita de novo.

## Cancelar ou substituir

Ainda não é possível por aqui. Use o portal nacional (gov.br/nfse) com o mesmo certificado.

**Próximo:** [para contadores](05-contadores.md) · [sua marca no PDF](06-marca-e-pdf.md)
