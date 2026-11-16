# 7. Problemas comuns

Procure a mensagem que apareceu (Control + F ou Command + F nesta página).

## Instalação

**"desenvolvedor não identificado" (Mac)**
Botão direito no arquivo → **Abrir** → **Abrir**. Só precisa fazer uma vez.

**"O Windows protegeu o computador"**
**Mais informações** → **Executar assim mesmo**.

**"uv: command not found" ou "'uv' não é reconhecido"**
Feche a janela e abra o instalador de novo. Se continuar, reinicie o computador: o uv foi instalado, mas o sistema ainda não "enxergou".

**"Permission denied" ao rodar `./instalar.sh` (Mac/Linux)**
No terminal, dentro da pasta: `chmod +x instalar.sh emissor *.command` e rode de novo.

**O instalador parou com erro de internet ou proxy**
Rede de empresa às vezes bloqueia downloads. Tente em outra rede ou peça à TI para liberar `astral.sh`, `github.com` e `pypi.org`.

**Algum teste falhou na instalação**
Copie a mensagem e abra uma *issue* no GitHub. Não emita em produção até resolver.

## Painel

**O navegador não abriu**
Abra manualmente: **http://127.0.0.1:8765**.

**"Endereço já em uso" / porta 8765 ocupada**
O emissor já está aberto em outra janela. Use aquela, ou feche-a. Ou abra em outra porta: `./emissor painel --porta 8766`.

**A página parou de responder**
Você fechou a janela preta. Abra o emissor de novo.

**"Buscar dados do CNPJ" ou "Buscar pelo CEP" não funcionou**
Os serviços públicos de consulta podem estar fora do ar. Preencha à mão. O código IBGE do município você acha pesquisando *"código IBGE"* e o nome da cidade.

## Certificado

**"Senha do certificado incorreta"**
Confira maiúsculas e minúsculas. Se você exportou o certificado, a senha é a que você criou na exportação.

**"O certificado venceu"**
Renove com a certificadora, cadastre o novo e troque o certificado padrão da empresa ([02-certificado.md](02-certificado.md)).

**"O certificado é de outro CNPJ"**
Você escolheu o certificado de outra empresa. Troque em **Editar dados → Certificado padrão** ou na tela de emissão.

**O Mac pede a senha do computador ao emitir**
É o cofre de senhas (Chaves) pedindo autorização. Digite a senha do Mac e clique em **Sempre permitir**.

**"Teste falhou: ... 401" ou "403"**
A Sefin não aceitou o certificado. Confirme que é um e-CNPJ A1 válido da empresa e que o município da empresa aderiu à NFS-e Nacional.

## Emissão

**A nota ficou como "verificar"**
A conexão caiu ou a Sefin demorou. **Não emita outra.** Abra a nota e clique em **Conferir com a Sefin**. Veja [04-primeira-nota.md](04-primeira-nota.md#se-a-internet-cair-no-meio).

**"Já existe nota para este cliente neste mês"**
Trava contra nota duplicada. Se for intencional (duas notas no mesmo mês), marque a liberação na prévia.

**"Valor fora da faixa do modelo"**
Trava contra erro de digitação. Confira o valor. Se estiver certo, marque a liberação na prévia ou ajuste a faixa no modelo.

**"conflito de numeração"**
O número de DPS já foi usado por outra nota (outro computador, outro sistema ou banco restaurado de backup antigo). Na página da empresa, em **Próxima DPS → Ajustar**, coloque um número maior que o último usado.

**Rejeição da Sefin com código (E0xxx)**
A mensagem diz o motivo. Os mais comuns:

| Sinal na mensagem | O que costuma ser | O que fazer |
|---|---|---|
| código de tributação não administrado / inexistente | Código nacional ou municipal errado para o seu município | Confira o código na sua última nota que deu certo ou com o contador |
| inscrição municipal | IM errada ou faltando | Corrija em **Editar dados** |
| Simples Nacional / regime | Regime da empresa diferente do cadastro na Receita | Confira o regime com o contador |
| município não conveniado | Prefeitura não aderiu à NFS-e Nacional | Use o sistema da prefeitura |
| DPS já existe / duplicidade | Número já usado | Veja "conflito de numeração" acima |

**"Situação não suportada: ISS retido" (ou não optante, estrangeiro etc.)**
O emissor bloqueia o que ainda não sabe emitir com segurança. Emita esse caso pelo portal nacional.

## Ainda com problema?

1. Rode `./emissor status` (Mac/Linux) ou `emissor status` (Windows) e copie o resultado. Ele não mostra senhas.
2. Os detalhes técnicos da comunicação ficam em `dados/logs/`. **Não publique esses arquivos**: eles têm dados das notas.
3. Abra uma *issue* no GitHub descrevendo o que fez e a mensagem de erro, **sem** CNPJ, nomes ou valores reais.
4. Precisa de ajuda rápida? [TechZyon](https://www.techzyon.com.br).
