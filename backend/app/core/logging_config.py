"""Logging configuration"""
import logging
import sys


class _SafeUtf8StreamHandler(logging.StreamHandler):
    """Avoid UnicodeEncodeError on Windows consoles (cp1252)."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except UnicodeEncodeError:
            try:
                msg = self.format(record)
                stream = self.stream
                enc = getattr(stream, "encoding", None) or "utf-8"
                stream.write(msg.encode(enc, errors="replace").decode(enc, errors="replace"))
                stream.write(self.terminator)
                self.flush()
            except Exception:
                self.handleError(record)


def setup_logging():
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    handler = _SafeUtf8StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
