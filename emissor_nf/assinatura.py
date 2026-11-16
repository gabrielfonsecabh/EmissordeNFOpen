"""Assinatura XMLDSig da DPS.

Mesmo padrão que a Sefin usa nas NFS-e que devolve: enveloped, RSA-SHA256,
digest SHA-256, canonicalização exclusiva, referência ao Id de infDPS e
<Signature> sem prefixo de namespace (prefixo gera rejeição E1228).
"""

from __future__ import annotations

from lxml import etree
from signxml import CanonicalizationMethod, DigestAlgorithm, SignatureMethod, XMLSigner, XMLVerifier

NS_DSIG = "http://www.w3.org/2000/09/xmldsig#"


def assinar(raiz: etree._Element, chave, cert_pem: bytes) -> etree._Element:
    alvo = next((el for el in raiz if el.get("Id")), None)
    if alvo is None:
        raise ValueError("Nenhum elemento com Id para assinar.")
    signer = XMLSigner(
        signature_algorithm=SignatureMethod.RSA_SHA256,
        digest_algorithm=DigestAlgorithm.SHA256,
        c14n_algorithm=CanonicalizationMethod.EXCLUSIVE_XML_CANONICALIZATION_1_0,
    )
    signer.namespaces = {None: NS_DSIG}
    assinado = signer.sign(
        raiz,
        key=chave,
        cert=[cert_pem.decode("ascii")],
        reference_uri=f"#{alvo.get('Id')}",
        always_add_key_value=False,
    )
    # Reparse para a árvore em memória enxergar <Signature> no namespace certo.
    return etree.fromstring(etree.tostring(assinado))


def verificar(xml: bytes, cert_pem: bytes) -> None:
    XMLVerifier().verify(xml, x509_cert=cert_pem.decode("ascii"), ignore_ambiguous_key_info=True)
