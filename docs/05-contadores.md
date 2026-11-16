# 5. Para contadores e escritórios

O emissor foi pensado para quem emite para **vários clientes**: cada cliente do escritório vira uma **empresa** no painel, com o próprio certificado, os próprios tomadores, serviços, modelos e até a própria marca no PDF.

## Organização recomendada

```
Certificados
 ├── Padaria Pão Bom (e-CNPJ)
 ├── Clínica Sorriso (e-CNPJ)
 └── Studio Alfa (e-CNPJ)

Empresas
 ├── Padaria Pão Bom   → certificado da Padaria → modelos: "Aluguel máquina", "Consultoria"
 ├── Clínica Sorriso   → certificado da Clínica → modelos: "Convênio X", "Particular"
 └── Studio Alfa       → certificado do Studio  → modelos: "Mensalidade Cliente Y"
```

1. Cadastre o certificado de cada cliente em **Certificados**. Use apelidos claros, como *Padaria Pão Bom 2026*.
2. Na lista de certificados, clique em **Criar empresa com ele**: o CNPJ já vem preenchido e o certificado já fica como padrão.
3. Para cada empresa, cadastre os tomadores, os serviços (com os códigos corretos daquele cliente) e os **modelos** das notas recorrentes.

Na hora de emitir: escolha a empresa, escolha o modelo, confira a prévia. O certificado padrão da empresa é usado automaticamente. Se precisar, dá para escolher outro na tela de emissão; o emissor só aceita certificado da mesma raiz de CNPJ (matriz e filiais).

## Uma pasta por cliente

Em **Editar dados** de cada empresa, preencha **Pasta onde salvar as notas**, por exemplo:

- Mac: `/Users/escritorio/Clientes/Padaria Pao Bom/Notas`
- Windows: `C:\Clientes\Padaria Pao Bom\Notas`

As notas são separadas em subpastas por ano e mês. Se a pasta estiver sincronizada com Google Drive, OneDrive ou Dropbox, o arquivo chega na nuvem sozinho.

## A marca de cada cliente no PDF

Em **Empresas → (cliente) → Marca do PDF**, coloque nome, logo e cores do cliente. A nota do cliente sai com a cara dele. Veja [06-marca-e-pdf.md](06-marca-e-pdf.md).

Se o escritório usa o emissor como parte de um serviço cobrado, mantenha marcada a opção **Manter a linha de créditos do projeto no rodapé**. Veja [CREDITOS-E-MARCA.md](../CREDITOS-E-MARCA.md).

## Perfis: o "template" de cada cliente

Um **perfil** é um arquivo `.json` com a empresa, os tomadores, os serviços, os modelos e a marca (inclusive o logo). **Não leva certificado nem senha.**

Use para:

- Levar o cadastro de um cliente para outro computador do escritório.
- Guardar um backup leve do cadastro.
- Montar o cadastro de um cliente novo a partir de um parecido.

**Exportar:** página da empresa → **Exportar perfil**.

**Importar:** **Empresas** → **Importar perfil** → escolha o arquivo. Depois, em **Editar dados**, escolha o certificado daquela empresa.

Tem um exemplo pronto em [`exemplos/perfil-exemplo.json`](../exemplos/perfil-exemplo.json). Você pode editar esse arquivo em qualquer editor de texto para montar perfis em lote.

> Se já existir uma empresa com o mesmo CNPJ, a importação é recusada para não misturar cadastros.

## Vários computadores no escritório

Cada computador tem o próprio banco e a própria numeração. Para não gerar conflito de número de DPS:

- **Melhor opção:** cada empresa é emitida sempre pelo **mesmo computador**.
- Se duas máquinas emitirem para a mesma empresa, use **séries diferentes** (ex.: série 1 no computador A e série 2 no computador B), em **Editar dados → Série da DPS**.

Mesmo se alguém errar, o emissor consulta a Sefin antes de reenviar e marca como **conflito** em vez de gerar nota duplicada.

## Precisa de algo maior?

Multiusuário, banco central, integração com o seu sistema contábil ou ERP, emissão em lote: a [TechZyon](https://www.techzyon.com.br) desenvolve sob medida.
