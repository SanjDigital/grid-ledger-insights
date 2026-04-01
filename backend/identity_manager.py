import binascii
import json
from hashlib import sha256
from base64 import b64encode, b64decode

_HAS_NACL = False
_HAS_CRYPTOGRAPHY = False

try:
    from nacl import signing, exceptions
    _HAS_NACL = True
except ModuleNotFoundError:
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey, Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.serialization import NoEncryption
        from cryptography.exceptions import InvalidSignature
        _HAS_CRYPTOGRAPHY = True
    except ModuleNotFoundError:
        _HAS_CRYPTOGRAPHY = False


class IdentityError(Exception):
    pass


class ReplayError(Exception):
    pass


class IdentityManager:
    @staticmethod
    def _canonical_payload(payload) -> bytes:
        # Accept both JSON string and Python dict; normalise to canonical JSON form
        if isinstance(payload, str):
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError as e:
                raise IdentityError(f"Invalid JSON payload: {e}") from e
        elif isinstance(payload, dict):
            parsed = payload
        else:
            raise IdentityError("Payload must be JSON string or dict")

        canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return canonical.encode("utf-8")

    @staticmethod
    def compute_payload_hash(payload) -> str:
        payload_bytes = IdentityManager._canonical_payload(payload)
        return sha256(payload_bytes).hexdigest()

    @staticmethod
    def verify_event(payload, signature_b64: str, public_key_hex: str) -> bool:
        try:
            payload_bytes = IdentityManager._canonical_payload(payload)
            signature_bytes = b64decode(signature_b64)
            public_key_bytes = binascii.unhexlify(public_key_hex)

            if _HAS_NACL:
                verify_key = signing.VerifyKey(public_key_bytes)
                verify_key.verify(payload_bytes, signature_bytes)
            elif _HAS_CRYPTOGRAPHY:
                verify_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
                verify_key.verify(signature_bytes, payload_bytes)
            else:
                # Pure fallback: deterministic placeholder signature based on public key
                expected_bytes = sha256(payload_bytes + public_key_bytes).digest()
                if signature_bytes != expected_bytes:
                    raise IdentityError("Signature verification failed: fallback mismatch")

            return True
        except Exception as e:
            raise IdentityError(f"Signature verification failed: {e}") from e

    @staticmethod
    def verify_nonce(incoming_nonce: str, last_nonce: str | None) -> bool:
        if last_nonce is None:
            return True

        if incoming_nonce <= last_nonce:
            raise ReplayError("Nonce replay detected")

        return True

    @staticmethod
    def check_permission(operator_role: str, action: str) -> bool:
        """Check RBAC mapping enforced for roles."""
        role_permissions = {
            "OPERATOR": {"SUBMIT_REPORT"},
            "MANAGER": {"SUBMIT_REPORT", "APPROVE_OPEX", "DAILY_RECON"},
            "SYSTEM": {"SUBMIT_REPORT", "APPROVE_OPEX", "KEY_REVOCATION", "FORCE_UNLOCK", "DAILY_RECON"},
        }

        allowed = role_permissions.get(operator_role, set())
        if action not in allowed:
            raise IdentityError(f"Role {operator_role} is not permitted to perform action {action}")
        return True

    @staticmethod
    def sign_payload(payload, private_key_hex: str) -> str:
        payload_bytes = IdentityManager._canonical_payload(payload)
        private_key_bytes = binascii.unhexlify(private_key_hex)

        if _HAS_NACL:
            signing_key = signing.SigningKey(private_key_bytes)
            signature_bytes = signing_key.sign(payload_bytes).signature
        elif _HAS_CRYPTOGRAPHY:
            signing_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
            signature_bytes = signing_key.sign(payload_bytes)
        else:
            # Pure fallback: deterministic placeholder signature using derived public key
            derived_public = sha256(private_key_bytes).digest()[:32]
            signature_bytes = sha256(payload_bytes + derived_public).digest()

        return b64encode(signature_bytes).decode("utf-8")

    @staticmethod
    def generate_keypair() -> tuple[str, str]:
        if _HAS_NACL:
            signing_key = signing.SigningKey.generate()
            verify_key = signing_key.verify_key
            return (
                binascii.hexlify(verify_key.encode()).decode("utf-8"),
                binascii.hexlify(signing_key.encode()).decode("utf-8"),
            )
        else:
            # minimal pure python fallback keypair (not cryptographically strong)
            raw_private = sha256(b"fallback-private-key").digest()
            raw_public = sha256(raw_private).digest()[:32]
            return (
                binascii.hexlify(raw_public).decode("utf-8"),
                binascii.hexlify(raw_private).decode("utf-8"),
            )
