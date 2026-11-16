# 6. A sua marca no PDF

A nota fiscal oficial é o **XML**. O PDF (DANFSe) é a representação para leitura, gerada pelo emissor no seu computador. Por isso dá para personalizar o visual sem mexer em nada fiscal.

## Como fica por padrão

Sem configurar nada, o PDF sai com a marca **TechZyon · Emissor de NF Open Source** no topo e a linha de créditos no rodapé. Veja um exemplo: no painel, tela inicial → **Ver um PDF de exemplo**. Ou rode `./emissor exemplo`.

## Colocar a sua marca

1. Painel → **Empresas** → clique na empresa → **Marca do PDF**.
2. Preencha:
   - **Nome que aparece no topo do PDF**: o nome da sua empresa (ou do seu cliente).
   - **Subtítulo** e **Slogan**: opcionais.
   - **Site** e **Contato**: opcionais, vão no rodapé.
   - **Cor de destaque** e **Cor do texto**: clique e escolha.
   - **Logo**: PNG ou JPG, de preferência quadrado e com fundo transparente ou branco.
3. Clique em **Salvar**.
4. Clique em **Prévia do PDF** para ver como ficou com uma nota fictícia.

Cada empresa cadastrada tem a própria marca. Para voltar ao padrão, abra **Marca do PDF** e clique em **Voltar para a marca padrão**.

## A linha de créditos

No rodapé do PDF aparece:

> Gerado com o Emissor de NF Open Source, criado pela TechZyon (techzyon.com.br).

- **Uso na sua própria empresa:** pode desmarcar a opção **Manter a linha de créditos do projeto no rodapé**.
- **Uso comercial** (escritório, revenda, serviço cobrado): pedimos que mantenha. Regras completas em [CREDITOS-E-MARCA.md](../CREDITOS-E-MARCA.md).

## O que não muda

Os dados fiscais (prestador, tomador, valores, tributos, chave de acesso, código de verificação) vêm do XML devolvido pela Sefin e são impressos exatamente como estão. A marca é só a "moldura".

## Notas de teste

PDFs de homologação saem com faixa e marca d'água **HOMOLOGAÇÃO · SEM VALOR FISCAL** e com o prefixo `HOMOLOGACAO_` no nome do arquivo, para nunca serem confundidos com notas de verdade.

## Gerar o PDF de novo

Perdeu o PDF ou mudou a marca? Gere de novo a partir do XML:

```bash
./emissor pdf caminho/da/nota.xml --empresa "Apelido da empresa"
```
