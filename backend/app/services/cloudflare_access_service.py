"""Cloudflare Access perimeter security service.

Provides cryptographic verification of Cloudflare Access JWT assertions:
- RS256 signature verification via JWKS public certificates
- Issuer verification (https://<team_domain>.cloudflareaccess.com)
- Audience (AUD) verification
- Expiration (exp) and timestamp validity
- Fail-closed security design: rejects requests if configurations are missing
- Anti-spoofing assertion matching with CF-Access-Authenticated-User-Email
"""

import json
import logging
import time
import urllib.request
from typing import Any, Dict, Optional

import jwt
from jwt.algorithms import RSAAlgorithm

from app.core.config import settings

logger = logging.getLogger(__name__)


class CloudflareAccessError(Exception):
    """Base exception for Cloudflare Access validation failures."""
    pass


class CloudflareMissingTokenError(CloudflareAccessError):
    """Raised when required Cloudflare Access JWT token is missing."""
    pass


class CloudflareInvalidTokenError(CloudflareAccessError):
    """Raised when Cloudflare Access JWT is invalid, expired, or failed signature check."""
    pass


class CloudflareConfigurationError(CloudflareAccessError):
    """Raised when Cloudflare Access is enforced but required settings are missing (fail-closed)."""
    pass


class CloudflareUntrustedOriginError(CloudflareAccessError):
    """Raised when request claims to come from Cloudflare perimeter but arrives from an untrusted socket."""
    pass


class JWKSCache:
    """In-memory cache for Cloudflare Access public signing certificates."""

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._keys: Dict[str, Any] = {}
        self._last_fetched: float = 0.0

    def get_key(self, kid: str, certs_url: Optional[str] = None) -> Optional[Any]:
        """Retrieve public key by kid, refreshing cache from certs_url if expired or missing."""
        now = time.time()
        # If key already in cache and cache is still within TTL, return it
        if kid in self._keys and (now - self._last_fetched) < self.ttl_seconds:
            return self._keys[kid]

        # Attempt to fetch if certs_url is provided
        if certs_url:
            self._fetch_and_cache(certs_url)
            if kid in self._keys:
                return self._keys[kid]

        # Key might exist from pre-injected test keys
        return self._keys.get(kid)

    def _fetch_and_cache(self, certs_url: str) -> None:
        """Fetch remote JWKS JSON and convert keys to cryptography RSA public keys."""
        try:
            req = urllib.request.Request(
                certs_url,
                headers={"User-Agent": f"FLODSS-Security/{settings.VERSION}"},
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            new_keys: Dict[str, Any] = {}
            for key_dict in data.get("keys", []):
                k_id = key_dict.get("kid")
                if k_id and key_dict.get("kty") == "RSA":
                    try:
                        pub_key = RSAAlgorithm.from_jwk(key_dict)
                        new_keys[k_id] = pub_key
                    except Exception as parse_err:
                        logger.warning(f"Failed to parse JWK kid={k_id}: {parse_err}")

            if new_keys:
                self._keys.update(new_keys)
                self._last_fetched = time.time()
                logger.info(f"Loaded {len(new_keys)} Cloudflare Access signing key(s) from JWKS.")
        except Exception as e:
            logger.error(f"Failed to fetch Cloudflare Access JWKS from {certs_url}: {e}")

    def inject_key(self, kid: str, public_key: Any) -> None:
        """Inject an RSA public key or JWK dictionary directly (for offline unit tests)."""
        if isinstance(public_key, dict):
            parsed = RSAAlgorithm.from_jwk(public_key)
            self._keys[kid] = parsed
        else:
            self._keys[kid] = public_key
        self._last_fetched = time.time()

    def inject_jwks(self, jwks: Dict[str, Any]) -> None:
        """Inject a full JWKS payload (for offline unit tests)."""
        for key_dict in jwks.get("keys", []):
            kid = key_dict.get("kid")
            if kid:
                self._keys[kid] = RSAAlgorithm.from_jwk(key_dict)
        self._last_fetched = time.time()

    def clear(self) -> None:
        """Clear cached keys."""
        self._keys.clear()
        self._last_fetched = 0.0


# Shared singleton cache
jwks_cache = JWKSCache()


class CloudflareAccessService:
    """Cryptographic perimeter service for Cloudflare Access assertion validation."""

    @staticmethod
    def get_token_from_request(request: Any) -> Optional[str]:
        """Extract Cloudflare Access JWT assertion from request header or cookie."""
        # Cloudflare Access transmits JWT assertion in 'Cf-Access-Jwt-Assertion'
        token = request.headers.get("cf-access-jwt-assertion")
        if token:
            return token.strip()
        # Fallback to standard Access cookie 'CF_Authorization'
        cookie_token = request.cookies.get("CF_Authorization")
        if cookie_token:
            return cookie_token.strip()
        return None

    @classmethod
    def verify_jwt(cls, token: str) -> Dict[str, Any]:
        """Verify Cloudflare Access JWT assertion signature, claims, and expiration.
        
        Enforces fail-closed configuration: raises CloudflareConfigurationError if
        expected audience or team domain is not configured.
        """
        # 1. Fail-closed configuration check
        expected_aud = settings.CLOUDFLARE_ACCESS_EXPECTED_AUD
        expected_issuer = settings.cloudflare_expected_issuer
        certs_url = settings.cloudflare_certs_url

        if not expected_aud or not expected_issuer:
            raise CloudflareConfigurationError(
                "Cloudflare Access perimeter is enforced but CLOUDFLARE_ACCESS_EXPECTED_AUD "
                "or CLOUDFLARE_ACCESS_TEAM_DOMAIN / CLOUDFLARE_ACCESS_TEAM_NAME is not configured (fail-closed)."
            )

        # 2. Extract and inspect unverified header
        try:
            unverified_header = jwt.get_unverified_header(token)
        except Exception as e:
            raise CloudflareInvalidTokenError(f"Malformed JWT header: {e}") from e

        alg = unverified_header.get("alg")
        if alg != "RS256":
            raise CloudflareInvalidTokenError(
                f"Unsupported JWT algorithm '{alg}'. Cloudflare Access requires RS256."
            )

        kid = unverified_header.get("kid")
        if not kid:
            raise CloudflareInvalidTokenError("JWT assertion header missing 'kid' (Key ID).")

        # 3. Retrieve public key
        public_key = jwks_cache.get_key(kid, certs_url=certs_url)
        if not public_key:
            raise CloudflareInvalidTokenError(
                f"Unable to verify JWT: Key ID '{kid}' not found in Cloudflare Access JWKS certificates."
            )

        # 4. Cryptographic signature and claims verification
        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=expected_aud,
                issuer=expected_issuer,
                options={
                    "require": ["exp", "iss", "aud"],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iss": True,
                    "verify_aud": True,
                },
            )
        except jwt.ExpiredSignatureError as e:
            raise CloudflareInvalidTokenError("Cloudflare Access JWT assertion has expired.") from e
        except jwt.InvalidAudienceError as e:
            raise CloudflareInvalidTokenError(
                f"Cloudflare Access JWT audience mismatch. Expected '{expected_aud}'."
            ) from e
        except jwt.InvalidIssuerError as e:
            raise CloudflareInvalidTokenError(
                f"Cloudflare Access JWT issuer mismatch. Expected '{expected_issuer}'."
            ) from e
        except jwt.InvalidSignatureError as e:
            raise CloudflareInvalidTokenError("Cloudflare Access JWT signature verification failed.") from e
        except jwt.InvalidTokenError as e:
            raise CloudflareInvalidTokenError(f"Invalid Cloudflare Access JWT: {e}") from e

        # 5. Extract authenticated user email
        email = payload.get("email") or payload.get("sub")
        if not email:
            raise CloudflareInvalidTokenError("Cloudflare Access JWT payload contains no email or subject claim.")

        return payload

    @classmethod
    def extract_and_verify_request(cls, request: Any) -> Optional[Dict[str, Any]]:
        """Extract and verify Cloudflare identity for an HTTP request under the active perimeter mode.

        Supports:
        - MANAGED_ACCESS: Cryptographic RS256 JWT assertion verification via JWKS (AUD, ISS, EXP).
        - PROTECTED_QUICK_TUNNEL: Validates Cloudflare edge OTP verification via CF-Access-Authenticated-User-Email
          delivered over trusted local proxy connection, with optional origin-side allowlist.
        - DISABLED: Returns None (perimeter disabled).

        For all active perimeter modes, requests arriving from untrusted socket origins (not in TRUSTED_PROXIES)
        are rejected to prevent identity header spoofing.
        """
        mode = settings.effective_perimeter_mode
        if mode == "DISABLED":
            return None

        # Anti-Spoofing Precondition for all active perimeter modes:
        # The physical socket connection MUST originate from a trusted local proxy (127.0.0.1, ::1, or testclient).
        direct_ip = request.client.host if (hasattr(request, "client") and request.client) else "unknown"
        if direct_ip not in settings.TRUSTED_PROXIES:
            raise CloudflareUntrustedOriginError(
                f"Untrusted connection origin ({direct_ip}): Cloudflare perimeter requests "
                f"must originate from trusted local proxy (127.0.0.1). Direct socket access rejected."
            )

        if mode == "MANAGED_ACCESS":
            # Mode A: Standard Managed Cloudflare Access with RS256 JWKS JWT verification
            token = cls.get_token_from_request(request)
            if not token:
                raise CloudflareMissingTokenError(
                    "Cloudflare Access perimeter authentication required: Missing or empty Cf-Access-Jwt-Assertion."
                )

            payload = cls.verify_jwt(token)
            verified_email = (payload.get("email") or payload.get("sub", "")).strip().lower()

            # Anti-spoofing check: If CF-Access-Authenticated-User-Email is present, it MUST match verified JWT
            header_email = request.headers.get("cf-access-authenticated-user-email")
            if header_email and header_email.strip().lower() != verified_email:
                raise CloudflareInvalidTokenError(
                    f"Header CF-Access-Authenticated-User-Email ({header_email}) does not match "
                    f"cryptographically verified token email ({verified_email}). Request rejected."
                )

            return payload

        elif mode == "PROTECTED_QUICK_TUNNEL":
            # Mode B: Cloudflare Protected Quick Tunnel (--allowed-mail)
            # Security Model:
            # 1. Cloudflare Edge enforces email OTP verification via --allowed-mail (Edge Perimeter Layer 1).
            # 2. Origin connection is restricted to trusted local proxy socket (127.0.0.1 / ::1).
            # 3. CF-Access-Authenticated-User-Email is NOT guaranteed by Cloudflare Quick Tunnels,
            #    nor is it cryptographically signed or bound to an Application AUD. Therefore, it is
            #    NEVER required, NEVER treated as proof of identity, and NEVER trusted to bypass FLODSS auth.
            # 4. Legitimate user identity and authorization are established SOLELY by FLODSS internal
            #    credentials (PBKDF2 passwords, single-use invitation tokens, sessions, RBAC) (Application Layer 2).
            raw_header = request.headers.get("cf-access-authenticated-user-email")
            advisory_email = raw_header.strip().lower() if raw_header else None

            # Optional advisory allowlist check if header is present and allowlist configured
            if advisory_email and settings.CLOUDFLARE_QUICK_TUNNEL_ALLOWED_EMAILS:
                allowed = settings.CLOUDFLARE_QUICK_TUNNEL_ALLOWED_EMAILS
                is_allowed = False
                for pattern in allowed:
                    if pattern.startswith("*@"):
                        domain = pattern[2:]
                        if advisory_email.endswith(f"@{domain}"):
                            is_allowed = True
                            break
                    elif advisory_email == pattern:
                        is_allowed = True
                        break
                if not is_allowed:
                    logger.warning(
                        f"Advisory header email '{advisory_email}' not in CLOUDFLARE_QUICK_TUNNEL_ALLOWED_EMAILS. "
                        f"FLODSS internal credentials remain mandatory."
                    )

            return {
                "mode": "PROTECTED_QUICK_TUNNEL",
                "socket_verified": True,
                "advisory_header_email": advisory_email,
                "auth_provider": "cloudflare_edge_otp",
            }


def setup_test_key_pair(kid: str = "flodss-test-key-1"):
    """Generate an ephemeral RSA key pair and register the public key in jwks_cache for tests."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    jwks_cache.inject_key(kid, public_key)
    return private_key, public_key


def create_test_jwt(
    email: str,
    private_key: Any,
    kid: str = "flodss-test-key-1",
    aud: Optional[str] = None,
    issuer: Optional[str] = None,
    expires_in_seconds: int = 3600,
    sub: Optional[str] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a signed RS256 JWT assertion for testing perimeter security."""
    now = int(time.time())
    effective_aud = aud if aud is not None else (settings.CLOUDFLARE_ACCESS_EXPECTED_AUD or "test-flodss-aud")
    effective_issuer = issuer if issuer is not None else (settings.cloudflare_expected_issuer or "https://test-team.cloudflareaccess.com")
    payload = {
        "aud": effective_aud,
        "iss": effective_issuer,
        "sub": sub or email,
        "email": email,
        "type": "app",
        "iat": now,
        "nbf": now,
        "exp": now + expires_in_seconds,
    }
    if extra_claims:
        payload.update(extra_claims)
    headers = {"alg": "RS256", "kid": kid, "typ": "JWT"}
    return jwt.encode(payload, private_key, algorithm="RS256", headers=headers)
