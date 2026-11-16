# Esquemas XSD da NFS-e Nacional

Arquivos oficiais publicados pela Receita Federal e pelo Comitê Gestor da NFS-e em gov.br/nfse. São usados só para validar a DPS **no seu computador, antes do envio**. Quem decide se a nota é aceita é sempre a Sefin Nacional.

| Pasta | Pacote oficial | Usado quando |
|---|---|---|
| `v1_01_nt009/` | `esquemas_prod_restrita_20261020.zip` ("NFSe-ESQUEMAS_XSD-PRODREST-v1.01-20261020"), página Produção Restrita | Homologação sempre; produção a partir de 01/12/2026 (Nota Técnica 009) |
| `v1_01/` | `nfse-esquemas_xsd-v1-01-20260209.zip` ("NFSe-ESQUEMAS_XSD-v1.01-20260209"), página Documentação Atual, pasta `Schemas/1.01` | Produção até 30/11/2026 |

Endereços:
- https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/producao-restrita/esquemas_prod_restrita_20261020.zip
- https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/documentacao-atual/nfse-esquemas_xsd-v1-01-20260209.zip

## O que foi mudado em relação ao oficial

- **Finais de linha** convertidos para LF em todos os arquivos.
- **`v1_01/tiposSimples_v1.01.xsd`, tipo `TSSerieDPS`:** o padrão oficial é `^0{0,4}\d{1,5}$`. Em XSD, `^` e `$` não são âncoras, são caracteres comuns, então nenhuma série real casa com esse padrão e toda DPS seria recusada na validação local. Foi trocado por `0{0,4}\d{1,5}`, que é o que o padrão claramente pretende. O pacote mais novo (pasta `v1_01_nt009/`) já corrigiu isso do lado oficial.
- **`v1_01/xmldsig-core-schema.xsd`:** substituído pelo arquivo do pacote de 20/10/2026, idêntico ao anterior exceto por não declarar a DTD externa (que o validador tentaria buscar).

Nenhum outro arquivo foi alterado.

## Atualizando

Quando a Sefin publicar um pacote novo, baixe o zip, descompacte numa pasta nova (por exemplo `v1_02/`), anote aqui a origem e a data, e ajuste `emissor_nf/dps.py` (função `leiaute`). Rode os testes depois.
