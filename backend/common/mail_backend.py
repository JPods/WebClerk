"""The one outbound mail path.

- The SMTP server and its login come from the active Connection with channel 'smtp'
  (config.endpoint = host, config.port, config.use_tls; encryption.credentials
  username/password). No key in .env or a Setting (Bill, 2026-09-18).
- Nothing is ever sent to a *.internal address. Agent logins (Alice, Andi) use
  <name>@<instance-uuid>.internal by default so mail meant for them can never leave
  the instance — it is dropped here and logged.
"""
from __future__ import annotations

import logging

from django.core.mail.backends.smtp import EmailBackend as SMTPBackend

logger = logging.getLogger(__name__)

INTERNAL_SUFFIX = '.internal'


def is_internal(address: str) -> bool:
    addr = (address or '').strip().rstrip('>').lower()
    return addr.endswith(INTERNAL_SUFFIX)


class ConnectionEmailBackend(SMTPBackend):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._configured = False

    def _configure(self):
        if self._configured:
            return
        from apps.sync.services.connections import active_connection, credentials
        conn = active_connection('smtp')           # raises ConnectionUnavailable — fail visibly
        cfg = conn.config or {}
        creds = credentials(conn)
        self.host = cfg.get('endpoint') or self.host
        self.port = int(cfg.get('port') or self.port)
        self.use_tls = bool(cfg.get('use_tls', True))
        self.use_ssl = False if self.use_tls else self.use_ssl
        self.username = creds.get('username') or ''
        self.password = creds.get('password') or ''
        self._configured = True

    def open(self):
        self._configure()
        return super().open()

    def send_messages(self, email_messages):
        outgoing = []
        for message in email_messages or []:
            for field in ('to', 'cc', 'bcc'):
                kept = [a for a in getattr(message, field) or [] if not is_internal(a)]
                dropped = [a for a in getattr(message, field) or [] if is_internal(a)]
                if dropped:
                    logger.info('[MAIL] not sent to agent address(es) %s: %s', dropped, message.subject)
                setattr(message, field, kept)
            if message.recipients():
                outgoing.append(message)
        if not outgoing:
            return 0
        return super().send_messages(outgoing)
