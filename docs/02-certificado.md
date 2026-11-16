# 2. Cadastrar o certificado digital

## Qual certificado serve

- **A1**, que é um **arquivo** (`.pfx` ou `.p12`) com senha. Serve.
- **A3**, que é **cartão ou token USB**. Ainda não é suportado.
- O certificado deve ser **e-CNPJ da empresa** que vai emitir. O emissor confere: se o CNPJ do certificado for diferente do CNPJ da empresa (considerando a matriz), ele bloqueia a emissão.

## Onde achar o arquivo

- Procure no e-mail da certificadora (Serasa, Certisign, Valid, Soluti, Safeweb etc.) da época da compra.
- Procure no computador por arquivos `.pfx` ou `.p12`.
  - **Mac:** abra o Finder, aperte Command + F e digite `.pfx`.
  - **Windows:** no Explorador de Arquivos, digite `*.pfx` na busca.
- O certificado está instalado só no navegador ou nas Chaves do Mac e você não tem o arquivo? Dá para exportar:
  - **Mac:** app **Acesso às Chaves** → **Meus Certificados** → botão direito no certificado da empresa → **Exportar** → formato **.p12** → crie uma senha.
  - **Windows:** `certmgr.msc` → **Pessoal** → **Certificados** → botão direito → **Todas as tarefas** → **Exportar** → **Sim, exportar a chave privada** → `.pfx` → crie uma senha.
- Não achou? A certificadora consegue ajudar.

## Cadastrar no emissor

1. No painel, clique em **Certificados**.
2. Em **Cadastrar certificado**:
   - **Arquivo:** escolha o `.pfx` ou `.p12`.
   - **Senha:** a senha do certificado.
   - **Apelido:** um nome para você reconhecer, por exemplo *Certificado Padaria 2026*.
3. Clique em **Cadastrar certificado**.

O emissor confere a senha, lê o CNPJ e a validade, guarda uma cópia do arquivo na pasta `dados/certificados/` e a senha no **cofre do sistema** (Chaves no Mac, Gerenciador de Credenciais no Windows). Você não precisa digitar a senha de novo.

> Na primeira emissão, o Mac pode perguntar se o emissor pode acessar o item das Chaves. Digite a senha do seu Mac e clique em **Sempre permitir**.

## Testar a conexão

Na lista de certificados, clique em **Testar conexão**. O emissor faz uma consulta inofensiva na Sefin de homologação (ambiente de teste) usando o certificado. Se aparecer *"Conexão com a Sefin funcionando"*, está tudo certo.

## Vários certificados

Pode cadastrar quantos quiser: um por empresa, ou o novo e o antigo durante a renovação. Na hora de emitir, o emissor usa o **certificado padrão da empresa**, e você pode escolher outro na tela de emissão.

## Quando o certificado vencer

O painel avisa quando faltar 30 dias. Ao renovar:

1. Cadastre o novo certificado.
2. Em **Empresas → (empresa) → Editar dados**, troque o **Certificado padrão**.
3. Depois, se quiser, remova o antigo.

**Próximo passo:** [cadastros e códigos](03-cadastros-e-codigos.md).
