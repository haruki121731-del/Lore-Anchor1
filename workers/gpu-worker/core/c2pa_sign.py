"""
C2PA Signing — Content Credentials for provenance.

Signs the protected image with a C2PA manifest declaring
``c2pa.training-mining: not-allowed``.

Uses the c2pa-python library.
Reference: https://opensource.contentauthenticity.org/docs/c2pa-python
"""
from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)


def _get_signing_credentials() -> tuple[bytes, bytes]:
    """Return (cert_pem, key_pem) from env vars or dev fallback."""
    cert_pem = os.environ.get("C2PA_CERT_PEM", "")
    key_pem = os.environ.get("C2PA_KEY_PEM", "")

    if cert_pem and key_pem:
        logger.info("Using production C2PA certificate from environment")
        return cert_pem.encode(), key_pem.encode()

    logger.warning(
        "C2PA_CERT_PEM / C2PA_KEY_PEM not set — using DEV self-signed cert. "
        "NOT suitable for production."
    )
    return _DEV_CERT, _DEV_KEY


def sign_c2pa(input_path: str, output_path: str) -> None:
    """Sign an image with a C2PA manifest.

    Args:
        input_path: Path to the image to sign.
        output_path: Path where the signed image will be written.
    """
    try:
        from c2pa import Builder, SigningAlg, create_signer

        manifest_json = json.dumps({
            "claim_generator": "lore-anchor/1.0",
            "title": "Protected by Lore Anchor",
            "assertions": [
                {
                    "label": "c2pa.training-mining",
                    "data": {
                        "entries": {
                            "c2pa.ai_generative_training": {
                                "use": "notAllowed",
                            },
                            "c2pa.ai_inference": {
                                "use": "notAllowed",
                            },
                            "c2pa.ai_training": {
                                "use": "notAllowed",
                            },
                            "c2pa.data_mining": {
                                "use": "notAllowed",
                            },
                        },
                    },
                },
            ],
        })

        builder = Builder(manifest_json)

        cert_pem, key_pem = _get_signing_credentials()
        signer = create_signer(
            sign_cert=cert_pem,
            private_key=key_pem,
            signing_alg=SigningAlg.ES256,
            ta_url=None,
        )

        builder.sign_file(signer, input_path, output_path)
        logger.info("C2PA manifest signed: %s -> %s", input_path, output_path)

    except ImportError:
        logger.warning(
            "c2pa-python not installed. Copying file without C2PA signature."
        )
        import shutil
        shutil.copy2(input_path, output_path)

    except Exception:
        logger.exception("C2PA signing failed, copying unsigned file.")
        import shutil
        shutil.copy2(input_path, output_path)


# ---------------------------------------------------------------------------
# Development self-signed certificate (ES256)
# Replace with real certs in production via environment variables.
# ---------------------------------------------------------------------------
_DEV_CERT = b"""-----BEGIN CERTIFICATE-----
MIIBejCCAR+gAwIBAgIUDEVLore0AnchorDevCert0000000wCgYIKoZIzj0EAwIw
FDESMBAGA1UEAwwJbG9yZS1kZXYwHhcNMjQwMTAxMDAwMDAwWhcNMjUwMTAxMMDAwMDBa
MBUxEzARBgNVBAMMCmxvcmUtZGV2MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE
PLACEHOLDER_DEV_KEY_REPLACE_IN_PRODUCTION_000000000000000000000000000000
000000000000000000000000000000000000aNTMFEwHQYDVR0OBBYEFDev0000000
MB8GA1UdIwQYMBaAFDev0000000MA8GA1UdEwEB/wQFMAMBAf8wCgYIKoZIzj0E
AwIDSQAwRgIhAPlaceholderSignatureForDevOnly000000000AiEA0000000000000
-----END CERTIFICATE-----"""

_DEV_KEY = b"""-----BEGIN EC PRIVATE KEY-----
PLACEHOLDER_DEV_PRIVATE_KEY_REPLACE_IN_PRODUCTION_00000000000000000000000
000000000000000000000000000000000000000000000000000000000000000000000
-----END EC PRIVATE KEY-----"""
