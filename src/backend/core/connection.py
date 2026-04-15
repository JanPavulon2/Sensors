# =========================================================
# core/connection.py
# =========================================================

from dataclasses import dataclass


@dataclass
class Connection:
    from_port: str
    to_port: str

