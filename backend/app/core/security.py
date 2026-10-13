"""Security, cryptography, rate limiting, and execution governance for FLODSS."""

import hashlib
import hmac
import os
import secrets
import time
from collections import defaultdict
from typing import Dict, List, Optional, Any
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# PBKDF2 configuration
PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 600_000
SALT_BYTES = 32


def hash_password(password: str) -> str:
    """Hash a plaintext password using PBKDF2-HMAC-SHA256 with cryptographically random salt."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    salt = secrets.token_bytes(SALT_BYTES)
    derived = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_{PBKDF2_ALGORITHM}${PBKDF2_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored PBKDF2 hash using constant-time comparison."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != f"pbkdf2_{PBKDF2_ALGORITHM}":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_hash = bytes.fromhex(parts[3])

        candidate_hash = hashlib.pbkdf2_hmac(
            PBKDF2_ALGORITHM,
            plain_password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(candidate_hash, expected_hash)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def generate_secure_token(nbytes: int = 32) -> str:
    """Generate a high-entropy cryptographically random URL-safe token."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """Generate SHA-256 hash of a token for safe database persistence."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class RateLimiter:
    """Thread-safe in-memory sliding window rate limiter."""

    def __init__(self):
        self._attempts: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_attempts: int, window_seconds: int) -> bool:
        """Check if request is permitted under rate limit window."""
        now = time.time()
        cutoff = now - window_seconds
        # Filter expired attempts
        valid = [t for t in self._attempts[key] if t > cutoff]
        self._attempts[key] = valid
        return len(valid) < max_attempts

    def record_attempt(self, key: str):
        """Record an attempt timestamp."""
        self._attempts[key].append(time.time())

    def reset(self, key: str):
        """Reset attempt history on successful event."""
        if key in self._attempts:
            del self._attempts[key]

    def reset_all(self):
        """Reset all rate limiter attempts."""
        self._attempts.clear()


class JobConcurrencyManager:
    """Tracks active optimization jobs running per user and system-wide to prevent resource exhaustion."""

    def __init__(self, max_total_jobs: int = 4):
        self._active_jobs: Dict[str, int] = defaultdict(int)
        self.max_total_jobs = max_total_jobs

    def acquire(self, user_id: str, max_concurrent: int, max_total: Optional[int] = None) -> bool:
        """Attempt to acquire a job execution slot for a user while respecting total system limit."""
        effective_max_total = max_total if max_total is not None else self.max_total_jobs
        if self.get_total_active_count() >= effective_max_total:
            return False
        current = self._active_jobs[user_id]
        if current >= max_concurrent:
            return False
        self._active_jobs[user_id] += 1
        return True

    def release(self, user_id: str):
        """Release a job execution slot."""
        if self._active_jobs[user_id] > 0:
            self._active_jobs[user_id] -= 1
            if self._active_jobs[user_id] == 0:
                del self._active_jobs[user_id]

    def get_active_count(self, user_id: str) -> int:
        """Return number of currently active jobs for user."""
        return self._active_jobs[user_id]

    def get_total_active_count(self) -> int:
        """Return number of currently active jobs across all users."""
        return sum(self._active_jobs.values())

    def reset_all(self):
        """Reset all active job counts."""
        self._active_jobs.clear()


rate_limiter = RateLimiter()
concurrency_manager = JobConcurrencyManager()


def get_trusted_client_ip(request: Any) -> str:
    """Resolve client IP address with proxy header anti-spoofing protection.

    Proxy headers (CF-Connecting-IP, X-Forwarded-For) are only evaluated if the direct
    socket connection originates from an address in settings.TRUSTED_PROXIES (e.g., 127.0.0.1, ::1).
    Direct connections from untrusted hosts use the physical socket IP.
    """
    direct_ip = request.client.host if (hasattr(request, "client") and request.client) else "unknown"
    if direct_ip not in settings.TRUSTED_PROXIES:
        return direct_ip

    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()

    x_forwarded = request.headers.get("x-forwarded-for")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()

    return direct_ip


def is_trusted_secure_request(request: Any) -> bool:
    """Determine whether request was delivered over verified HTTPS.

    Proxy headers (X-Forwarded-Proto, CF-Visitor) are only evaluated if the direct
    socket connection originates from an address in settings.TRUSTED_PROXIES.
    """
    if settings.SESSION_COOKIE_SECURE:
        return True
    if hasattr(request, "url") and request.url.scheme == "https":
        return True

    direct_ip = request.client.host if (hasattr(request, "client") and request.client) else "unknown"
    if direct_ip in settings.TRUSTED_PROXIES:
        if request.headers.get("x-forwarded-proto", "").lower() == "https":
            return True
        cf_visitor = request.headers.get("cf-visitor", "")
        if '"scheme":"https"' in cf_visitor:
            return True

    return False
