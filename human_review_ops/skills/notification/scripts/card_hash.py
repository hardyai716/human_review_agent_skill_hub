#!/usr/bin/env python3
"""Card payload hash helpers for notification drafts."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any


META_KEY = "_meta"
DATA_HASH_KEY = "_data_hash"


def canonicalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): canonicalize(value[key])
            for key in sorted(value, key=lambda item: str(item))
        }
    if isinstance(value, list):
        return [canonicalize(item) for item in value]
    return value


def compute_hits_hash(hits: list[dict[str, Any]]) -> str:
    if not isinstance(hits, list):
        raise TypeError("hits must be a list of dict")
    if not all(isinstance(item, dict) for item in hits):
        raise TypeError("each hit must be a dict")

    canonical_hits = [canonicalize(item) for item in hits]
    canonical_hits.sort(
        key=lambda item: json.dumps(
            item,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    payload = json.dumps(
        canonical_hits,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def embed_hash_in_card(
    card_json: dict[str, Any],
    hits_hash: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(card_json, dict):
        raise TypeError("card_json must be a dict")
    if not isinstance(hits_hash, str) or not hits_hash:
        raise TypeError("hits_hash must be a non-empty string")

    card = copy.deepcopy(card_json)
    meta = card.setdefault(META_KEY, {})
    if not isinstance(meta, dict):
        raise TypeError("card_json['_meta'] must be a dict when present")
    meta[DATA_HASH_KEY] = hits_hash
    if metadata:
        meta.update(metadata)
    return card


def strip_internal_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: strip_internal_keys(val)
            for key, val in value.items()
            if not str(key).startswith("_")
        }
    if isinstance(value, list):
        return [strip_internal_keys(item) for item in value]
    return value


def verify_card_hash(card_json: dict[str, Any], current_hits: list[dict[str, Any]]) -> bool:
    meta = card_json.get(META_KEY)
    if not isinstance(meta, dict) or not meta.get(DATA_HASH_KEY):
        raise ValueError("card missing _meta._data_hash")
    expected_hash = meta[DATA_HASH_KEY]
    current_hash = compute_hits_hash(current_hits)
    if expected_hash != current_hash:
        raise ValueError(
            f"card data hash mismatch: expected {expected_hash}, got {current_hash}"
        )
    return True
