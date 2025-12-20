from __future__ import annotations

from pydantic import BaseModel


class ComarcaOut(BaseModel):
    code: str
    name: str
