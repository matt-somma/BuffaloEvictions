from __future__ import annotations

import csv
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Mapping

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = ROOT / "config" / "public_label_settings.json"
ALIASES_PATH = ROOT / "config" / "public_neighborhood_aliases.csv"
TRACT_ALIASES_PATH = ROOT / "config" / "public_tract_aliases.csv"
DISPLAY_NAME_PATTERN = re.compile(r"^(?P<base>.+?) \((?P<geoid>[^()]+)\)$")
LABEL_MODE_SESSION_KEY = "label_display_mode"
NEIGHBORHOOD_LABEL_MODE = "neighborhood"
PUBLIC_LABEL_MODE = "public"


def _parse_bool(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "f", "no", "n", "off"}:
        return False
    return default


@lru_cache(maxsize=1)
def _load_file_settings() -> dict[str, object]:
    if not SETTINGS_PATH.exists():
        return {}

    with SETTINGS_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    return payload if isinstance(payload, dict) else {}


@lru_cache(maxsize=1)
def _load_alias_map() -> dict[str, str]:
    aliases: dict[str, str] = {}

    if not ALIASES_PATH.exists():
        return aliases

    with ALIASES_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            real_name = (row.get("real_name") or "").strip()
            public_label = (row.get("public_label") or "").strip()
            if real_name and public_label:
                aliases[real_name] = public_label

    return aliases


def _get_public_settings(secrets: Mapping[str, object] | None = None) -> dict[str, object]:
    settings = {
        "default_mode": PUBLIC_LABEL_MODE,
        "include_geoid": False,
        "alias_prefix": "NBH",
        "tract_prefix": "CT",
    }
    settings.update(_load_file_settings())

    if isinstance(secrets, Mapping):
        try:
            public_settings = secrets.get("public_labels")
        except Exception:
            public_settings = None

        if isinstance(public_settings, Mapping):
            settings.update(public_settings)

    env_enabled = os.getenv("PUBLIC_MASK_NEIGHBORHOODS")
    env_include_geoid = os.getenv("PUBLIC_INCLUDE_GEOID")
    env_alias_prefix = os.getenv("PUBLIC_ALIAS_PREFIX")
    env_tract_prefix = os.getenv("PUBLIC_TRACT_PREFIX")
    env_default_mode = os.getenv("PUBLIC_LABEL_MODE")

    if env_enabled is not None:
        settings["default_mode"] = PUBLIC_LABEL_MODE if _parse_bool(env_enabled, False) else NEIGHBORHOOD_LABEL_MODE
    if env_include_geoid is not None:
        settings["include_geoid"] = env_include_geoid
    if env_alias_prefix:
        settings["alias_prefix"] = env_alias_prefix
    if env_tract_prefix:
        settings["tract_prefix"] = env_tract_prefix
    if env_default_mode:
        settings["default_mode"] = env_default_mode

    default_mode = str(settings.get("default_mode") or PUBLIC_LABEL_MODE).strip().lower()
    if default_mode not in {PUBLIC_LABEL_MODE, NEIGHBORHOOD_LABEL_MODE}:
        default_mode = PUBLIC_LABEL_MODE

    return {
        "default_mode": default_mode,
        "include_geoid": _parse_bool(settings.get("include_geoid"), False),
        "alias_prefix": str(settings.get("alias_prefix") or "NBH").strip() or "NBH",
        "tract_prefix": str(settings.get("tract_prefix") or "CT").strip() or "CT",
    }


def _extract_base_label(display_name: object, geoid: object) -> tuple[str | None, str | None]:
    if display_name is None or pd.isna(display_name):
        return None, None

    label = str(display_name).strip()
    geoid_text = None if geoid is None or pd.isna(geoid) else str(geoid).strip()

    if geoid_text:
        suffix = f" ({geoid_text})"
        if label.endswith(suffix):
            return label[: -len(suffix)], geoid_text

    match = DISPLAY_NAME_PATTERN.match(label)
    if match:
        return match.group("base").strip(), match.group("geoid").strip()

    return label, geoid_text


def _alias_lookup(names: list[str], configured_aliases: dict[str, str], prefix: str) -> dict[str, str]:
    aliases = dict(configured_aliases)
    used_aliases = set(aliases.values())

    unresolved = sorted({name for name in names if name and name not in aliases})
    next_index = 1

    for name in unresolved:
        while True:
            candidate = f"{prefix}-{next_index:02d}"
            next_index += 1
            if candidate not in used_aliases:
                break

        aliases[name] = candidate
        used_aliases.add(candidate)

    return aliases


@lru_cache(maxsize=1)
def _load_tract_alias_map() -> dict[str, str]:
    aliases: dict[str, str] = {}

    if not TRACT_ALIASES_PATH.exists():
        return aliases

    with TRACT_ALIASES_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            geoid = (row.get("geoid") or "").strip()
            public_label = (row.get("public_label") or "").strip()
            if geoid and public_label:
                aliases[geoid] = public_label

    return aliases


def _build_tract_keys(
    label_parts: list[tuple[str | None, str | None]],
    tract_prefix: str,
) -> dict[tuple[str, str], str]:
    grouped_geoids: dict[str, set[str]] = {}

    for base_name, geoid_text in label_parts:
        if base_name and geoid_text:
            grouped_geoids.setdefault(base_name, set()).add(geoid_text)

    tract_keys: dict[tuple[str, str], str] = {}

    for base_name, geoids in grouped_geoids.items():
        for index, geoid_text in enumerate(sorted(geoids), start=1):
            tract_keys[(base_name, geoid_text)] = f"{tract_prefix}-{index:02d}"

    return tract_keys


def public_labeling_enabled(secrets: Mapping[str, object] | None = None) -> bool:
    return get_label_mode(secrets) == PUBLIC_LABEL_MODE


def get_label_mode(
    secrets: Mapping[str, object] | None = None,
    session_state: Mapping[str, object] | None = None,
) -> str:
    settings = _get_public_settings(secrets)
    mode = settings["default_mode"]

    if isinstance(session_state, Mapping):
        session_mode = session_state.get(LABEL_MODE_SESSION_KEY)
        if isinstance(session_mode, str) and session_mode in {PUBLIC_LABEL_MODE, NEIGHBORHOOD_LABEL_MODE}:
            mode = session_mode

    return mode


def public_label_cache_key(secrets: Mapping[str, object] | None = None) -> str:
    settings = _get_public_settings(secrets)
    file_markers = []

    for path in (SETTINGS_PATH, ALIASES_PATH, TRACT_ALIASES_PATH):
        if path.exists():
            stat = path.stat()
            file_markers.append(f"{path.name}:{int(stat.st_mtime_ns)}:{stat.st_size}")
        else:
            file_markers.append(f"{path.name}:missing")

    return "|".join(
        [
            f"default_mode={settings['default_mode']}",
            f"include_geoid={int(settings['include_geoid'])}",
            f"alias_prefix={settings['alias_prefix']}",
            f"tract_prefix={settings['tract_prefix']}",
            *file_markers,
        ]
    )


def mask_dataframe_public_labels(
    df: pd.DataFrame,
    *,
    secrets: Mapping[str, object] | None = None,
    session_state: Mapping[str, object] | None = None,
) -> pd.DataFrame:
    settings = _get_public_settings(secrets)

    if get_label_mode(secrets, session_state) != PUBLIC_LABEL_MODE or "display_name" not in df.columns:
        return df

    masked = df.copy()
    label_parts: list[tuple[str | None, str | None]] = []
    base_names: list[str] = []

    geoid_series = masked["geoid"] if "geoid" in masked.columns else pd.Series([None] * len(masked))

    for display_name, geoid in zip(masked["display_name"], geoid_series, strict=False):
        base_name, geoid_text = _extract_base_label(display_name, geoid)
        label_parts.append((base_name, geoid_text))
        if base_name:
            base_names.append(base_name)

    aliases = _alias_lookup(base_names, _load_alias_map(), settings["alias_prefix"])
    tract_keys = _build_tract_keys(label_parts, settings["tract_prefix"])
    tract_aliases = _load_tract_alias_map()

    public_display_names: list[object] = []
    public_neighborhoods: list[object] = []
    public_tract_keys: list[object] = []

    for original, (base_name, geoid_text) in zip(masked["display_name"], label_parts, strict=False):
        if not base_name:
            public_display_names.append(original)
            public_neighborhoods.append(base_name)
            public_tract_keys.append(None)
            continue

        alias = aliases.get(base_name, base_name)
        tract_key = tract_keys.get((base_name, geoid_text)) if geoid_text else None
        direct_tract_alias = tract_aliases.get(geoid_text) if geoid_text else None
        public_neighborhoods.append(alias)
        public_tract_keys.append(direct_tract_alias or tract_key)

        if direct_tract_alias:
            public_display_names.append(direct_tract_alias)
        elif settings["include_geoid"] and geoid_text:
            public_display_names.append(f"{alias} ({geoid_text})")
        elif tract_key:
            public_display_names.append(f"{alias} / {tract_key}")
        else:
            public_display_names.append(alias)

    masked["display_name"] = public_display_names

    if "dominant_neighborhood" in masked.columns:
        masked["dominant_neighborhood"] = [
            aliases.get(str(value), value) if value is not None and not pd.isna(value) else value
            for value in masked["dominant_neighborhood"]
        ]

    if "public_neighborhood" not in masked.columns:
        masked["public_neighborhood"] = public_neighborhoods
    if "public_tract_key" not in masked.columns:
        masked["public_tract_key"] = public_tract_keys

    return masked
