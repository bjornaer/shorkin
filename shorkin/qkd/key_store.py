"""Thread-safe session key storage with rotation and expiration."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class _KeyEntry:
    key: bytes
    protocol: str
    created_at: float = field(default_factory=time.time)
    use_count: int = 0


class KeyStore:
    """Thread-safe storage for QKD session keys."""

    def __init__(
        self,
        max_age_seconds: float = 3600.0,
        max_uses: int = 1000,
    ):
        self._max_age = max_age_seconds
        self._max_uses = max_uses
        self._keys: dict[str, _KeyEntry] = {}
        self._lock = threading.Lock()

    def store(self, session_id: str, key: bytes, protocol: str) -> None:
        """Store a new session key."""
        with self._lock:
            self._keys[session_id] = _KeyEntry(key=key, protocol=protocol)

    def get(self, session_id: str) -> bytes | None:
        """Retrieve a session key, incrementing use count.

        Returns None if the session doesn't exist or has expired.
        """
        with self._lock:
            entry = self._keys.get(session_id)
            if entry is None:
                return None
            if self._is_expired(entry):
                del self._keys[session_id]
                return None
            entry.use_count += 1
            return entry.key

    def get_protocol(self, session_id: str) -> str | None:
        """Get the protocol used for a session."""
        with self._lock:
            entry = self._keys.get(session_id)
            return entry.protocol if entry else None

    def rotate(self, session_id: str, new_key: bytes) -> None:
        """Replace a session key (key rotation)."""
        with self._lock:
            entry = self._keys.get(session_id)
            if entry is None:
                raise KeyError(f"Session {session_id} not found")
            entry.key = new_key
            entry.created_at = time.time()
            entry.use_count = 0

    def is_expired(self, session_id: str) -> bool:
        """Check if a session key has expired."""
        with self._lock:
            entry = self._keys.get(session_id)
            if entry is None:
                return True
            return self._is_expired(entry)

    def remove(self, session_id: str) -> None:
        """Remove a session key."""
        with self._lock:
            self._keys.pop(session_id, None)

    def cleanup_expired(self) -> int:
        """Remove all expired keys. Returns the number removed."""
        with self._lock:
            expired = [
                sid for sid, entry in self._keys.items() if self._is_expired(entry)
            ]
            for sid in expired:
                del self._keys[sid]
            return len(expired)

    def active_sessions(self) -> list[str]:
        """Return a list of active (non-expired) session IDs."""
        with self._lock:
            return [
                sid
                for sid, entry in self._keys.items()
                if not self._is_expired(entry)
            ]

    def _is_expired(self, entry: _KeyEntry) -> bool:
        age = time.time() - entry.created_at
        return age > self._max_age or entry.use_count >= self._max_uses
