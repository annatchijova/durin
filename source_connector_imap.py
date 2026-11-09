"""Fail-closed, read-only IMAP source connector.

This is the authorized-source boundary for a real mailbox, parallel to
`source_ingestion.list_sources` for a local directory. It never deletes,
flags, or moves a message; it only reads bytes and turns them into the same
attested source records the rest of Durin already validates.
"""

from __future__ import annotations

import imaplib
import os
from dataclasses import dataclass
from typing import Any, Callable

from source_ingestion import MAX_SOURCES, build_source_record


DEFAULT_MAILBOX = "INBOX"
DEFAULT_PORT = 993


@dataclass(frozen=True)
class IMAPSourceConfig:
    host: str
    username: str
    password: str
    port: int = DEFAULT_PORT
    mailbox: str = DEFAULT_MAILBOX

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "IMAPSourceConfig":
        values = os.environ if environ is None else environ
        config = cls(
            host=values.get("DURIN_IMAP_HOST", ""),
            username=values.get("DURIN_IMAP_USERNAME", ""),
            password=values.get("DURIN_IMAP_PASSWORD", ""),
            port=int(values.get("DURIN_IMAP_PORT", str(DEFAULT_PORT)) or DEFAULT_PORT),
            mailbox=values.get("DURIN_IMAP_MAILBOX", DEFAULT_MAILBOX),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if not self.host or len(self.host) > 253:
            raise ValueError("DURIN_IMAP_HOST is required and bounded")
        if not self.username or not self.password:
            raise ValueError("DURIN_IMAP_USERNAME and DURIN_IMAP_PASSWORD are required")
        if isinstance(self.port, bool) or not isinstance(self.port, int) or not (0 < self.port <= 65535):
            raise ValueError("DURIN_IMAP_PORT must be a valid port number")
        if not self.mailbox or len(self.mailbox) > 128:
            raise ValueError("DURIN_IMAP_MAILBOX is required and bounded")


def list_imap_sources(
    config: IMAPSourceConfig,
    *,
    max_messages: int = MAX_SOURCES,
    client_factory: Callable[[str, int], Any] | None = None,
) -> list[dict[str, Any]]:
    """Read up to `max_messages` most-recent messages as attested sources.

    Connects over IMAPS only (no plaintext fallback), selects the mailbox
    read-only so no message flag or location is mutated, and never issues a
    delete, move, or flag-setting command.
    """
    if isinstance(max_messages, bool) or not isinstance(max_messages, int) or not (0 < max_messages <= MAX_SOURCES):
        raise ValueError(f"max_messages must be between 1 and {MAX_SOURCES}")
    factory = client_factory or imaplib.IMAP4_SSL
    connection = factory(config.host, config.port)
    try:
        connection.login(config.username, config.password)
        status, _ = connection.select(config.mailbox, readonly=True)
        if status != "OK":
            raise ValueError(f"cannot open mailbox read-only: {config.mailbox}")
        status, data = connection.search(None, "ALL")
        if status != "OK":
            raise ValueError("IMAP search failed")
        message_ids = data[0].split() if data and data[0] else []
        if len(message_ids) > MAX_SOURCES:
            raise ValueError(f"mailbox exceeds the {MAX_SOURCES} message limit for one connector run")
        selected_ids = message_ids[-max_messages:]
        sources: list[dict[str, Any]] = []
        for message_id in selected_ids:
            status, message_data = connection.fetch(message_id, "(RFC822)")
            if status != "OK" or not message_data or not isinstance(message_data[0], tuple):
                raise ValueError(f"cannot fetch message {message_id!r}")
            raw = message_data[0][1]
            sources.append(build_source_record(
                raw,
                source_location=f"imap://{config.host}/{config.mailbox}/{message_id.decode('ascii', errors='replace')}",
                kind="EMAIL",
                content_available=True,
            ))
        return sources
    finally:
        try:
            connection.close()
        except Exception:
            pass
        try:
            connection.logout()
        except Exception:
            pass
