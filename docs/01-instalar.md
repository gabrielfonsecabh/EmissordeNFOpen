# 1. Instalar

Tempo: uns 10 minutos. Você não precisa saber programar.

## Antes de começar, tenha em mãos

- **Um computador** com Mac, Windows 10/11 ou Linux, ligado na internet.
- **O certificado digital A1** da empresa: um arquivo terminado em `.pfx` ou `.p12`, e a **senha** dele. É o mesmo certificado que você usa para entrar no portal da NFS-e ou no e-CAC. Não sabe onde está? Veja [02-certificado.md](02-certificado.md).
- **Os dados da empresa**: CNPJ, inscrição municipal (se a prefeitura usa) e o regime (ME/EPP ou MEI).

## Passo 1: baixar

1. Nesta página do projeto no GitHub, clique no botão verde **Code**.
2. Clique em **Download ZIP**.
3. Ache o arquivo baixado (geralmente na pasta Downloads) e descompacte:
   - **Mac:** dois cliques no `.zip`.
   - **Windows:** botão direito no `.zip` → **Extrair tudo** → **Extrair**.
4. Mova a pasta descompactada para um lugar fácil, por exemplo `Documentos`. Pode renomear para `Emissor de NF`.

> Importante: não deixe a pasta dentro de Downloads se você costuma limpar essa pasta. Suas notas e cadastros ficam dentro dela, na subpasta `dados`.

## Passo 2: instalar

### Mac

1. Abra a pasta do emissor.
2. Dê dois cliques em **`Instalar no Mac.command`**.
3. Se aparecer *"não pode ser aberto porque é de um desenvolvedor não identificado"*:
   - Clique em **OK**.
   - Clique com o **botão direito** (ou Control + clique) no mesmo arquivo e escolha **Abrir**.
   - Na nova janela, clique em **Abrir**.
4. Uma janela preta (o Terminal) vai mostrar o progresso. Na primeira vez ele baixa o Python e as bibliotecas. Espere aparecer **"Pronto!"**.
5. O navegador abre sozinho no emissor.

### Windows

1. Abra a pasta do emissor.
2. Dê dois cliques em **`Instalar no Windows.bat`**.
3. Se aparecer *"O Windows protegeu o computador"*: clique em **Mais informações** e depois em **Executar assim mesmo**.
4. Espere aparecer **"Pronto!"** na janela preta. O navegador abre sozinho.

### Linux

No terminal, dentro da pasta do emissor:

```bash
./instalar.sh
```

### O que o instalador faz

1. Instala o **uv**, uma ferramenta gratuita que cuida do Python (só se você ainda não tiver).
2. Baixa o Python e as bibliotecas que o emissor usa, **só dentro da pasta do emissor**. Não mexe no resto do computador.
3. Roda os testes automáticos para conferir que está tudo certo.
4. Gera um PDF de exemplo em `dados/exemplos/`.
5. Abre o painel no navegador.

## Passo 3: abrir nas próximas vezes

- **Mac:** dois cliques em **`Abrir Emissor.command`**.
- **Windows:** dois cliques em **`Abrir Emissor.bat`**.
- **Terminal:** `./emissor painel` (Mac/Linux) ou `emissor painel` (Windows).

O painel abre em **http://127.0.0.1:8765**. Esse endereço só funciona no seu próprio computador, é normal.

**Deixe a janela preta aberta enquanto usa o emissor.** Para desligar, feche a janela (ou aperte Control + C dentro dela).

> Dica: no Mac, arraste o `Abrir Emissor.command` para o Dock (lado direito, perto da lixeira) para ter um atalho. No Windows, botão direito no `Abrir Emissor.bat` → **Enviar para** → **Área de trabalho (criar atalho)**.

## Deu algum erro?

Veja [07-problemas-comuns.md](07-problemas-comuns.md). Se nada resolver, copie a mensagem da janela preta e cole na sua IA junto com o texto de [PROMPT-PARA-SUA-IA.md](../PROMPT-PARA-SUA-IA.md).

**Próximo passo:** [cadastrar o certificado](02-certificado.md).
