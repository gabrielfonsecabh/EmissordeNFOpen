# Como contribuir

Obrigado por ajudar! Algumas regras simples:

1. **Nunca envie dados reais** em *issues*, *pull requests* ou testes: CNPJ, CPF, nomes, valores, XML de notas, certificados ou logs. Use os dados fictícios de `tests/conftest.py` e `exemplos/`.
2. Rode os testes antes de enviar: `uv run pytest`. Todos precisam passar.
3. Mudou a montagem do XML? Os testes de comparação com a nota real anonimizada e de validação nos esquemas oficiais precisam continuar passando.
4. Textos para o usuário em português do Brasil, simples, pensando em quem não é da área.
5. Nada de telemetria, servidores próprios ou dependência de nuvem.
6. Leia [AGENTS.md](AGENTS.md) se for usar IA para programar.

Ao contribuir, você concorda que sua contribuição seja licenciada sob a [Licença Apache 2.0](LICENSE).

Dúvidas: abra uma *issue* ou fale com a [TechZyon](https://www.techzyon.com.br).
