"""Shared WITSML XML helpers — docs/DATA_INVENTORY.md records the real archive's structure
quirks this module exists to handle: the same physical wellbore is registered under multiple
operator-prefix folders over the field's life, and a numbered wellbore subfolder's index does
not reliably map to the public NPD suffix letter (the real name only lives in each folder's own
`_wellboreInfo/*.xml`). `find_wellbore_dirs` resolves a well's real name to every matching
folder across all registrations, so callers never have to hardcode a prefix/index mapping.
"""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET

# WITSML XML is namespaced; stripping namespaces up front (rather than threading `{ns}tag`
# through every call site) keeps the rest of this module readable.
_NS_RE = re.compile(r"\{[^}]+\}")


def parse_stripped(path: Path) -> ET.Element:
    """Parses an XML file and strips namespaces from every tag, returning the root element."""
    tree = ET.parse(path)
    root = tree.getroot()
    for el in root.iter():
        el.tag = _NS_RE.sub("", el.tag)
    return root


def find_wellbore_dirs(witsml_root: Path, wellbore_name: str) -> list[Path]:
    """Every folder under `witsml_root` whose `_wellboreInfo/*.xml` declares `<nameWellbore>`
    equal to `wellbore_name` (e.g. "NO 15/9-F-11 A" or "15/9-F-11 A" — matched case-insensitively
    and ignoring a leading "NO " country prefix some registrations add). A well re-registered
    under Statoil/StatoilHydro/Statoil-NO over the field's life resolves to multiple directories
    here; callers must read from all of them, not just one."""
    target = normalize_wellbore_name(wellbore_name)
    matches: list[Path] = []
    for info_file in witsml_root.glob("*/*/_wellboreInfo/*.xml"):
        try:
            root = parse_stripped(info_file)
        except ET.ParseError:
            continue
        wellbore_el = root.find("wellbore")
        name_el = wellbore_el.find("name") if wellbore_el is not None else None
        if name_el is None or name_el.text is None:
            continue
        if normalize_wellbore_name(name_el.text) == target:
            matches.append(info_file.parent.parent)
    return matches


def normalize_wellbore_name(name: str) -> str:
    """Volve's WITSML archive has at least two source systems registering the same physical
    wellbore under slightly different names — BHI-sourced registrations use the plain NPD name
    ("15/9-F-11 A"), sometimes with a "NO " country prefix ("NO 15/9-F-11 A"); InterAct-sourced
    ones append " - Main Wellbore" ("15/9-F-14 - Main Wellbore"). Both must resolve to the same
    canonical key so `find_wellbore_dirs` returns every registration, not just the first one
    found (confirmed needed for F-5/F-12/F-14 in docs/DATA_INVENTORY.md)."""
    name = name.strip()
    if name.upper().startswith("NO "):
        name = name[3:]
    name = re.sub(r"\s*-?\s*main\s+wellbore\s*$", "", name, flags=re.IGNORECASE)
    return name.strip().upper()


def log_sets(bore_dir: Path) -> list[Path]:
    """The `log/<n>/` folders under one wellbore directory — each is an independent group of
    named log objects (see docs/DATA_INVENTORY.md: "time-indexed logs are not one clean
    composite feed")."""
    log_root = bore_dir / "log"
    if not log_root.is_dir():
        return []
    return [p for p in sorted(log_root.iterdir()) if p.is_dir()]


def log_objects(log_set_dir: Path) -> list[Path]:
    """The numbered log-object folders under one `log/<n>/` set, each a distinct named log
    (`MetaFileInfo.txt` in the same folder maps number -> name, informational only — the log's
    own XML header is the source of truth for name/mnemonics)."""
    return [p for p in sorted(log_set_dir.iterdir()) if p.is_dir()]


def log_data_files(log_object_dir: Path) -> list[Path]:
    """All `*.xml` data-chunk files under one log object, in file order (chunks are numbered
    sequentially and each is a self-contained WITSML `<logs><log>...</log></logs>` document with
    its own header + `<data>` rows)."""
    return sorted(log_object_dir.rglob("*.xml"))
