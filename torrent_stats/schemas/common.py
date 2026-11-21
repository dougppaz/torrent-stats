from __future__ import annotations

import base64
import re
from typing import Annotated

from pydantic import BaseModel, BeforeValidator
from pydantic_core import PydanticCustomError


def normalize_info_hash(v: str) -> str:
    if not isinstance(v, str):
        raise PydanticCustomError("string_type", "Info hash must be a string")
    val = v.strip()
    if len(val) != 40:
        try:
            padding = "=" * ((8 - len(val) % 8) % 8)
            val = base64.b32decode(val.upper() + padding).hex()
        except Exception as exc:
            raise PydanticCustomError(
                "value_error",
                "Invalid info hash format (must be 40-char hex or 32-char base32)",
            ) from exc

    if len(val) != 40 or not re.match(r"^[0-9a-fA-F]{40}$", val):
        raise PydanticCustomError(
            "value_error",
            "Invalid info hash format (must be 40-char hex or 32-char base32)",
        )
    return val.lower()


ValidatedInfoHash = Annotated[str, BeforeValidator(normalize_info_hash)]


class ActionSuccessResponse(BaseModel):
    status: str
    info_hash: str
