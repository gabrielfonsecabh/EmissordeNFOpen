# Segurança

## Onde ficam as coisas

| O quê | Onde | Sai do seu computador? |
|---|---|---|
| Certificado A1 (cópia) | `dados/certificados/<id>.pfx`, só o seu usuário lê | Não |
| Senha do certificado | Cofre do sistema: Chaves (Mac), Gerenciador de Credenciais (Windows), Secret Service (Linux) | Não |
| Empresas, clientes, modelos, histórico | `dados/emissor.db` (SQLite) | Não |
| Notas (XML e PDF) | `dados/notas/<CNPJ>/<ano>/<mês>/` ou a pasta que você escolher | Não |
| Logs de comunicação | `dados/logs/` | Não |

O emissor só se comunica com:

- **Sefin Nacional** (`sefin.nfse.gov.br` e `sefin.producaorestrita.nfse.gov.br`): para emitir e consultar notas, com o seu certificado (conexão mTLS).
- **BrasilAPI** e **ViaCEP**: só quando você clica em "Buscar dados do CNPJ" ou "Buscar pelo CEP". Vai apenas o CNPJ ou o CEP digitado.

Não existe servidor da TechZyon no meio. Não há telemetria.

## O painel

- Escuta só em `127.0.0.1` (a própria máquina). Outros computadores da rede não acessam.
- Recusa requisições com outro endereço de Host (proteção contra *DNS rebinding*).
- Todo formulário tem token anti-CSRF.
- Emitir em produção exige digitar `EMITIR`.

## Boas práticas

- Faça **backup** da pasta `dados/` (veja [docs/08-backup-e-atualizacao.md](docs/08-backup-e-atualizacao.md)). Guarde o backup em lugar seguro: ele contém o certificado.
- Use **criptografia de disco** (FileVault no Mac, BitLocker no Windows).
- Se o computador é compartilhado, cada pessoa deve usar o próprio usuário do sistema.
- Se suspeitar que o certificado vazou, revogue com a sua certificadora e remova do emissor.
- Nunca mande o `.pfx` ou a senha por e-mail, WhatsApp ou para uma IA.

## Encontrou uma falha?

Não abra *issue* pública. Escreva pelo site [techzyon.com.br](https://www.techzyon.com.br) com o assunto "Segurança: Emissor de NF Open Source".
