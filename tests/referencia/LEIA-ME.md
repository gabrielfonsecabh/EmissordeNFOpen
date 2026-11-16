# Referência de teste

`nfse_referencia_anonimizada.xml` é uma NFS-e **real**, aceita pela Sefin Nacional em outubro de 2026 (emitida pelo Emissor Web do governo), com **todos os dados trocados por fictícios**: CNPJs, nomes, endereços, inscrição municipal, telefone, e-mail, descrição, valores, municípios, números, datas e chave. A assinatura digital foi removida.

O que foi preservado é o que importa para o teste: a **estrutura** (ordem e presença dos elementos) da DPS que a Sefin aceitou. `tests/test_dps.py` monta uma DPS com os mesmos dados fictícios pelo código deste projeto e exige que ela saia idêntica, byte a byte depois de canonicalizada.

Os CNPJs usados (11.222.333/0001-81 e 33.444.555/0001-81) são números de exemplo com dígito verificador válido, sem relação com empresas reais conhecidas.
