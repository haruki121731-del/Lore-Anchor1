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

logger = logging.getLogger(__name__)


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

        # NOTE: In production, use a real certificate and private key.
        # For development, c2pa-python can generate a self-signed signer.
        signer = create_signer(
            sign_cert=_DEV_CERT,
            private_key=_DEV_KEY,
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
