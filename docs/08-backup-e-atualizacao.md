# 8. Backup e atualização

## O que importa guardar

Tudo o que é seu está na pasta **`dados/`**, dentro da pasta do emissor:

| Dentro de `dados/` | O que é |
|---|---|
| `emissor.db` | Cadastros, modelos, numeração e histórico de emissões |
| `certificados/` | Cópia dos certificados A1 |
| `notas/` e `homologacao/` | XML e PDF das notas (se você não definiu outra pasta) |
| `marcas/` | Logos |
| `logs/` | Registro técnico da comunicação com a Sefin |

As senhas dos certificados ficam no cofre do sistema, não na pasta. Ao restaurar em **outro computador**, vá em **Certificados** e cadastre de novo o mesmo arquivo `.pfx` com a senha. O emissor reconhece que é o mesmo certificado e mantém as empresas ligadas a ele.

## Fazer backup

1. **Feche o emissor** (feche a janela preta).
2. Copie a pasta `dados/` inteira para um pendrive, HD externo ou nuvem.
3. Guarde com cuidado: ela contém os certificados.

Recomendado: uma vez por mês e sempre antes de atualizar.

Os XML das notas são documentos fiscais. Guarde-os pelo prazo legal (pergunte ao contador; em geral, no mínimo 5 anos). Eles também ficam disponíveis no portal nacional.

## Restaurar

1. Instale o emissor normalmente.
2. Feche o emissor.
3. Copie a sua pasta `dados/` de backup para dentro da pasta do emissor, substituindo a que existir.
4. Abra o emissor.

> **Cuidado com backup antigo.** Se você emitiu notas depois daquele backup, a numeração do banco restaurado estará atrasada. O emissor detecta o conflito ao consultar a Sefin e não duplica a nota, mas o mais simples é ajustar a **Próxima DPS** na página da empresa antes de emitir.

## Atualizar para uma versão nova

Seus dados ficam em `dados/`, separados do programa. Para atualizar:

**Se baixou o ZIP:**

1. Faça backup de `dados/`.
2. Baixe o ZIP novo e descompacte em outra pasta.
3. Copie a sua pasta `dados/` para dentro da pasta nova.
4. Rode o instalador da pasta nova.
5. Confira se está tudo lá e apague a pasta antiga.

**Se usa git:**

```bash
git pull
./instalar.sh --sem-abrir
```

Leia as novidades na página de *Releases* do GitHub antes de atualizar.

## Mudanças da Sefin

O padrão da NFS-e Nacional muda de tempos em tempos (como a NT 009, obrigatória em produção a partir de 01/12/2026, que este emissor já suporta). Mantenha o emissor atualizado. Se uma atualização da Sefin quebrar algo, a correção sai em uma versão nova aqui no GitHub.
