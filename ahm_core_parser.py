#!/usr/bin/env python3
"""
AHM 1.0 Core Parser
===============

Purpose
-------
Parse the simple, self-describing AHM core without trying to understand every
local/domain-specific construct.

Design rule:
    PARSE THE CORE.
    PRESERVE THE REST.
    LET THE AI INTERPRET LOCAL SEMANTICS.

The parser is intentionally tolerant:
- known AHM structures are extracted when recognizable;
- unknown/local constructs are preserved verbatim;
- local extensions do not make a file invalid merely because the parser does
  not understand their semantics;
- the original text can be round-tripped unchanged.

No third-party packages are required.

Examples
--------
    python ahm_core_parser.py project.ahm
    python ahm_core_parser.py project.ahm --json
    python ahm_core_parser.py project.ahm --check
    python ahm_core_parser.py project.ahm --roundtrip-check
    python ahm_core_parser.py --self-test
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


KNOWN_SECTION_NAMES = {
    "INSTRUCTIONS", "INSTRUCTION", "DESCRIPTION", "SPEC", "FIELD_DICTIONARY",
    "KEY", "MEMORY", "DOMAIN_DATA", "OBJECTS", "OBJECT_INDEX", "NODE_INDEX",
    "BOOK_INDEX", "ENTITY_INDEX", "ENTITY_REGISTER", "ELEMENT_ROWS",
    "RELATIONS", "RELATION_BLOCK", "RELATION_DICTIONARY", "RELKEY",
    "THEMES", "THEME_INDEX", "THEME_TRACKING", "FACTS", "STATE", "STATUS",
    "VALIDATION", "NEXT", "ACTIONS", "PROCESS", "PROCESS_ORDER",
    "INFORMATION_BANK", "SOURCES", "PROJECT_RULES", "CONSTRAINTS", "LOCKED",
    "VERIFY", "VERIFICATION", "OUTPUT", "UPDATE", "UPDATE_INPUT",
    "REQUIRED_OUTPUT", "CONCLUSION", "INDEX", "REPORT", "CHANGELOG",
    "EXECUTION", "PRIMARY_OBJECTIVE", "CANVAS_BINDING", "GEOMETRIC_BINDING",
    "NEGATIVE_CONSTRAINTS", "GLOBAL_LAYOUT", "RENDERING_LOCKS",
}

CORE_PREFIXES = {
    "P": "project",
    "O": "object",
    "F": "fact",
    "R": "relation",
    "S": "state",
    "N": "next",
    "K": "knowledge",
    "A": "action",
    "V": "verify",
}

SEPARATOR_RE = re.compile(r"^[=\-_*]{5,}$")
BRACKET_SECTION_RE = re.compile(r"^\[([A-Za-z0-9_. /+\-]+)\]$")
NUMBERED_SECTION_RE = re.compile(r"^\d+(?:\.\d+)*\.\s+(.+)$")
DIRECTIVE_RE = re.compile(r"^([A-Za-z0-9_.\-]+)::(.*)$")
INDEXED_REL_RE = re.compile(r"^(R\d+):(.*)$")
KEY_ASSIGN_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_.\-]*)\s*=\s*(.+)$")
SOURCE_RE = re.compile(r"^SOURCE\s+([A-Za-z0-9_.\-]+)\s*$", re.I)


@dataclass
class AHMRecord:
    line_no: int
    section: Optional[str]
    kind: str
    raw: str
    parsed: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AHMDocument:
    path: Optional[str]
    text: str
    records: List[AHMRecord]
    sections: List[str]
    keys: Dict[str, str]
    objects: Dict[str, Dict[str, Any]]
    facts: List[Dict[str, Any]]
    relations: List[Dict[str, Any]]
    states: List[Dict[str, Any]]
    next_items: List[str]
    actions: List[str]
    sources: Dict[str, Dict[str, Any]]
    local_records: List[AHMRecord]
    warnings: List[str]

    def render(self) -> str:
        """Return the original file text unchanged."""
        return self.text

    def summary(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "sections": self.sections,
            "key_count": len(self.keys),
            "object_count": len(self.objects),
            "fact_count": len(self.facts),
            "relation_count": len(self.relations),
            "state_count": len(self.states),
            "next_count": len(self.next_items),
            "action_count": len(self.actions),
            "source_count": len(self.sources),
            "local_or_unparsed_count": len(self.local_records),
            "warning_count": len(self.warnings),
        }

    def to_jsonable(self) -> Dict[str, Any]:
        return {
            "summary": self.summary(),
            "keys": self.keys,
            "objects": self.objects,
            "facts": self.facts,
            "relations": self.relations,
            "states": self.states,
            "next": self.next_items,
            "actions": self.actions,
            "sources": self.sources,
            "warnings": self.warnings,
            "records": [asdict(r) for r in self.records],
        }



@dataclass
class ValidationIssue:
    level: str          # ERROR | WARNING | INFO
    code: str
    message: str
    line_no: Optional[int] = None

    def render(self) -> str:
        where = f" line {self.line_no}" if self.line_no is not None else ""
        return f"{self.level} {self.code}{where}: {self.message}"


def soft_validate(doc: AHMDocument) -> List[ValidationIssue]:
    """
    Tolerant AHM validation.

    Philosophy:
        - validate what the Core parser actually recognizes;
        - never reject an unknown local/domain construct merely because it is unknown;
        - preserve local extensions for AI interpretation;
        - distinguish hard defects in recognized Core syntax from soft interoperability warnings.
    """
    issues: List[ValidationIssue] = []

    # 1. Basic AHM signal.
    recognized = [
        r for r in doc.records
        if r.kind in {
            "section", "key", "project", "object", "fact", "relation",
            "state", "next", "action", "knowledge", "source", "directive"
        }
    ]
    if not recognized:
        issues.append(ValidationIssue(
            "WARNING", "W_NO_AHM_SIGNAL",
            "No recognizable AHM core or self-describing construct was found."
        ))

    # 2. Duplicate object IDs.
    object_lines = {}
    for r in doc.records:
        if r.kind == "object":
            oid = r.parsed.get("id")
            if not oid:
                issues.append(ValidationIssue(
                    "ERROR", "E_OBJECT_ID_MISSING",
                    "Recognized object record has no object ID.", r.line_no
                ))
                continue
            if oid in object_lines:
                issues.append(ValidationIssue(
                    "ERROR", "E_OBJECT_ID_DUPLICATE",
                    f"Object ID {oid!r} was already declared on line {object_lines[oid]}.",
                    r.line_no
                ))
            else:
                object_lines[oid] = r.line_no

    declared = set(object_lines)

    # 3. Duplicate KEY definitions with different meanings.
    seen_keys = {}
    for r in doc.records:
        if r.kind == "key":
            k = r.parsed.get("key")
            v = r.parsed.get("value")
            if k in seen_keys and seen_keys[k] != v:
                issues.append(ValidationIssue(
                    "WARNING", "W_KEY_REDEFINED",
                    f"KEY {k!r} is redefined from {seen_keys[k]!r} to {v!r}.",
                    r.line_no
                ))
            elif k is not None:
                seen_keys[k] = v

    # 4. Recognized compact object syntax.
    for r in doc.records:
        if r.kind == "object":
            oid = r.parsed.get("id", "")
            if not str(oid).strip():
                issues.append(ValidationIssue(
                    "ERROR", "E_OBJECT_EMPTY_ID",
                    "Object ID is empty.", r.line_no
                ))

    # 5. Recognized compact fact syntax.
    current_fact_keys = {}
    for r in doc.records:
        if r.kind != "fact":
            continue
        subject = r.parsed.get("subject")
        fields = r.parsed.get("fields", {})
        tags = r.parsed.get("tags", [])

        if not subject:
            issues.append(ValidationIssue(
                "ERROR", "E_FACT_SUBJECT_MISSING",
                "Recognized F: record has no subject.", r.line_no
            ))
        elif declared and subject not in declared and not subject.startswith(("NODE.", "@", "SRC_", "SPARE_")):
            issues.append(ValidationIssue(
                "WARNING", "W_FACT_SUBJECT_UNDECLARED",
                f"Fact subject {subject!r} is not declared as an O: object; it may be a valid local/external identifier.",
                r.line_no
            ))

        # If the same subject/property has more than one CUR value, flag it.
        for prop, value in fields.items():
            if "CUR" in tags:
                key = (subject, prop)
                if key in current_fact_keys and current_fact_keys[key][0] != value:
                    prev_value, prev_line = current_fact_keys[key]
                    issues.append(ValidationIssue(
                        "WARNING", "W_MULTIPLE_CURRENT_VALUES",
                        f"{subject}:{prop} has multiple current values: {prev_value!r} (line {prev_line}) and {value!r}.",
                        r.line_no
                    ))
                else:
                    current_fact_keys[key] = (value, r.line_no)

        # Explicit unresolved U should not carry a guessed non-empty value.
        if "U" in tags:
            for prop, value in fields.items():
                if value not in ("", "UNKNOWN", "UNRESOLVED", "?"):
                    issues.append(ValidationIssue(
                        "WARNING", "W_UNRESOLVED_HAS_VALUE",
                        f"Fact marked U/unresolved also contains value {value!r}; verify this is intentional.",
                        r.line_no
                    ))

    # 6. Recognized compact relation syntax.
    for r in doc.records:
        if r.kind != "relation":
            continue
        src = r.parsed.get("source")
        tgt = r.parsed.get("target")
        typ = r.parsed.get("type")

        if r.raw.strip().startswith("R:"):
            if not src or not tgt:
                issues.append(ValidationIssue(
                    "ERROR", "E_REL_ENDPOINT_MISSING",
                    "Recognized R: relation is missing source or target.", r.line_no
                ))
            if not typ:
                issues.append(ValidationIssue(
                    "ERROR", "E_REL_TYPE_MISSING",
                    "Recognized R: relation is missing relation type.", r.line_no
                ))

        # Undeclared endpoints are warnings only: AHM may intentionally reference
        # external/local identifiers that are defined by another domain construct.
        if declared:
            if src and src not in declared and not str(src).startswith(("NODE.", "@")):
                issues.append(ValidationIssue(
                    "WARNING", "W_REL_SOURCE_UNDECLARED",
                    f"Relation source {src!r} is not a declared O: object; preserved as a possible local/external ID.",
                    r.line_no
                ))
            if tgt and tgt not in declared and not str(tgt).startswith(("NODE.", "@")):
                issues.append(ValidationIssue(
                    "WARNING", "W_REL_TARGET_UNDECLARED",
                    f"Relation target {tgt!r} is not a declared O: object; preserved as a possible local/external ID.",
                    r.line_no
                ))

    # 7. STATE syntax and subject checks.
    seen_state = {}
    for r in doc.records:
        if r.kind != "state":
            continue
        subject = r.parsed.get("subject")
        value = r.parsed.get("value")
        if subject is None or value is None:
            issues.append(ValidationIssue(
                "ERROR", "E_STATE_MALFORMED",
                "Recognized S: record must use S:ID=STATE form.", r.line_no
            ))
            continue
        if subject in seen_state and seen_state[subject][0] != value:
            prev_value, prev_line = seen_state[subject]
            issues.append(ValidationIssue(
                "INFO", "I_STATE_UPDATED_IN_FILE",
                f"State for {subject!r} changes from {prev_value!r} (line {prev_line}) to {value!r}.",
                r.line_no
            ))
        seen_state[subject] = (value, r.line_no)

    # 8. Duplicate NEXT/ACTION items.
    for kind, items in (("NEXT", doc.next_items), ("ACTION", doc.actions)):
        seen = set()
        for item in items:
            if item in seen:
                issues.append(ValidationIssue(
                    "WARNING", f"W_DUPLICATE_{kind}",
                    f"Duplicate {kind} item {item!r}."
                ))
            seen.add(item)

    # 9. Local extensions are explicitly allowed.
    if doc.local_records:
        issues.append(ValidationIssue(
            "INFO", "I_LOCAL_EXTENSIONS_PRESERVED",
            f"{len(doc.local_records)} local/unparsed constructs were preserved for AI interpretation."
        ))

    # 10. Round-trip property of this parser.
    if doc.render() != doc.text:
        issues.append(ValidationIssue(
            "ERROR", "E_ROUNDTRIP_INTERNAL",
            "Parser failed to preserve the decoded source text."
        ))

    return issues


def validation_result(issues: List[ValidationIssue]) -> str:
    if any(i.level == "ERROR" for i in issues):
        return "FAIL"
    if any(i.level == "WARNING" for i in issues):
        return "PASS_WITH_WARNINGS"
    return "PASS"


def _strip_eol(line: str) -> str:
    return line[:-2] if line.endswith("\r\n") else line[:-1] if line.endswith(("\n", "\r")) else line


def _is_separator(s: str) -> bool:
    return bool(SEPARATOR_RE.fullmatch(s.strip()))


def _upper_ratio(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return 0.0
    return sum(c.isupper() for c in letters) / len(letters)


def _looks_like_section(line: str, prev_nonblank: str, next_nonblank: str) -> Optional[str]:
    s = line.strip()
    if not s:
        return None

    m = BRACKET_SECTION_RE.match(s)
    if m:
        return m.group(1).strip()

    normalized = s.replace(" ", "_").upper()
    if normalized in KNOWN_SECTION_NAMES:
        return normalized

    m = NUMBERED_SECTION_RE.match(s)
    if m:
        title = m.group(1).strip()
        if _upper_ratio(title) >= 0.75 and (_is_separator(prev_nonblank) or _is_separator(next_nonblank)):
            return title.replace(" ", "_")

    if _is_separator(prev_nonblank) and _is_separator(next_nonblank):
        return s

    return None


def _split_quoted(text: str, sep: str) -> List[str]:
    """Split on one-character sep, ignoring separators inside double quotes."""
    out, buf = [], []
    quoted = False
    escaped = False
    for ch in text:
        if escaped:
            buf.append(ch)
            escaped = False
            continue
        if ch == "\\":
            buf.append(ch)
            escaped = True
            continue
        if ch == '"':
            quoted = not quoted
            buf.append(ch)
            continue
        if ch == sep and not quoted:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf))
    return out


def _parse_fact(s: str) -> Dict[str, Any]:
    parts = _split_quoted(s, ":")
    data: Dict[str, Any] = {"raw": s}
    if len(parts) >= 2:
        data["subject"] = parts[1]
    fields: Dict[str, str] = {}
    tags: List[str] = []
    for token in parts[2:]:
        if "=" in token:
            k, v = token.split("=", 1)
            fields[k] = v
        elif token != "":
            tags.append(token)
        else:
            tags.append("")
    data["fields"] = fields
    data["tags"] = tags
    return data


def _parse_simple_relation(s: str) -> Dict[str, Any]:
    parts = _split_quoted(s, ":")
    data: Dict[str, Any] = {"raw": s}
    if len(parts) >= 2 and ">" in parts[1]:
        src, tgt = parts[1].split(">", 1)
        data["source"] = src
        data["target"] = tgt
    if len(parts) >= 3:
        data["type"] = parts[2]
    if len(parts) > 3:
        data["tags"] = parts[3:]
    return data


def _parse_indexed_relation(s: str) -> Dict[str, Any]:
    m = INDEXED_REL_RE.match(s)
    if not m:
        return {"raw": s}
    rid, body = m.groups()
    fields: Dict[str, str] = {}
    for piece in body.split(";"):
        piece = piece.strip()
        if not piece:
            continue
        if "=" in piece:
            k, v = piece.split("=", 1)
            fields[k.strip()] = v.strip()
        else:
            fields.setdefault("_extra", "")
            fields["_extra"] += piece
    out: Dict[str, Any] = {"raw": s, "id": rid, "fields": fields}
    if "F" in fields:
        out["source"] = fields["F"]
    if "T" in fields:
        out["target"] = fields["T"]
    if "Y" in fields:
        out["type"] = fields["Y"]
    if "S" in fields:
        out["status"] = fields["S"]
    return out


def _parse_directive_body(body: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {"raw_body": body.strip()}
    clauses: Dict[str, str] = {}
    for piece in _split_quoted(body, "|"):
        piece = piece.strip()
        if "::" in piece:
            k, v = piece.split("::", 1)
            clauses[k.strip()] = v.strip()
    if clauses:
        result["clauses"] = clauses
    return result


def parse_ahm_text(text: str, path: Optional[str] = None) -> AHMDocument:
    lines = text.splitlines(keepends=True)
    plain = [_strip_eol(x) for x in lines]

    prev_nonblank = [""] * len(plain)
    next_nonblank = [""] * len(plain)
    last = ""
    for i, s in enumerate(plain):
        prev_nonblank[i] = last
        if s.strip():
            last = s.strip()
    nxt = ""
    for i in range(len(plain) - 1, -1, -1):
        next_nonblank[i] = nxt
        if plain[i].strip():
            nxt = plain[i].strip()

    records: List[AHMRecord] = []
    sections: List[str] = []
    keys: Dict[str, str] = {}
    objects: Dict[str, Dict[str, Any]] = {}
    facts: List[Dict[str, Any]] = []
    relations: List[Dict[str, Any]] = []
    states: List[Dict[str, Any]] = []
    next_items: List[str] = []
    actions: List[str] = []
    sources: Dict[str, Dict[str, Any]] = {}
    local_records: List[AHMRecord] = []
    warnings: List[str] = []

    current_section: Optional[str] = None
    current_source: Optional[str] = None

    for i, raw_line in enumerate(lines, start=1):
        s = _strip_eol(raw_line)
        stripped = s.strip()

        if not stripped:
            records.append(AHMRecord(i, current_section, "blank", s))
            continue

        if stripped.startswith("//") or stripped.startswith("#"):
            records.append(AHMRecord(i, current_section, "comment", s))
            continue

        if _is_separator(stripped):
            records.append(AHMRecord(i, current_section, "divider", s))
            continue

        sec = _looks_like_section(
            s,
            prev_nonblank[i - 1] if i - 1 < len(prev_nonblank) else "",
            next_nonblank[i - 1] if i - 1 < len(next_nonblank) else "",
        )
        if sec:
            current_section = sec
            current_source = None
            if sec not in sections:
                sections.append(sec)
            records.append(AHMRecord(i, current_section, "section", s, {"name": sec}))
            continue

        sm = SOURCE_RE.match(stripped)
        if sm:
            sid = sm.group(1)
            current_source = sid
            sources.setdefault(sid, {})
            rec = AHMRecord(i, current_section, "source", s, {"id": sid})
            records.append(rec)
            continue

        if current_source and ":" in stripped and not stripped.startswith(tuple(f"{p}:" for p in CORE_PREFIXES)):
            k, v = stripped.split(":", 1)
            if k.strip() and " " not in k.strip():
                sources[current_source][k.strip()] = v.strip()
                records.append(AHMRecord(i, current_section, "source_field", s, {
                    "source": current_source, "key": k.strip(), "value": v.strip()
                }))
                continue

        if stripped.startswith("O:"):
            parts = _split_quoted(stripped, ":")
            parsed = {"raw": stripped}
            if len(parts) >= 2:
                parsed["id"] = parts[1]
                parsed["label"] = ":".join(parts[2:]) if len(parts) > 2 else ""
                if parts[1] in objects:
                    warnings.append(f"line {i}: duplicate object id {parts[1]}")
                objects[parts[1]] = parsed
            records.append(AHMRecord(i, current_section, "object", s, parsed))
            continue

        if stripped.startswith("F:"):
            parsed = _parse_fact(stripped)
            parsed["line_no"] = i
            facts.append(parsed)
            records.append(AHMRecord(i, current_section, "fact", s, parsed))
            continue

        if stripped.startswith("R:"):
            parsed = _parse_simple_relation(stripped)
            parsed["line_no"] = i
            relations.append(parsed)
            records.append(AHMRecord(i, current_section, "relation", s, parsed))
            continue

        if stripped.startswith("S:"):
            body = stripped[2:]
            if "=" in body:
                obj, value = body.split("=", 1)
                parsed = {"subject": obj, "value": value}
            else:
                parsed = {"raw_body": body}
            parsed["line_no"] = i
            states.append(parsed)
            records.append(AHMRecord(i, current_section, "state", s, parsed))
            continue

        if stripped.startswith("N:"):
            item = stripped[2:]
            next_items.append(item)
            records.append(AHMRecord(i, current_section, "next", s, {"item": item}))
            continue

        if stripped.startswith("A:"):
            item = stripped[2:]
            actions.append(item)
            records.append(AHMRecord(i, current_section, "action", s, {"item": item}))
            continue

        if stripped.startswith("K:"):
            records.append(AHMRecord(i, current_section, "knowledge", s, {"value": stripped[2:]}))
            continue

        if stripped.startswith("P:"):
            records.append(AHMRecord(i, current_section, "project", s, {"id": stripped[2:]}))
            continue

        legacy_obj = re.match(r"^(O[A-Za-z0-9_.\\-]+)::(.*)$", stripped)
        if legacy_obj:
            oid, label = legacy_obj.groups()
            parsed = {"raw": stripped, "id": oid, "label": label.strip(), "local_style": True}
            if oid in objects:
                warnings.append(f"line {i}: duplicate object id {oid}")
            objects[oid] = parsed
            records.append(AHMRecord(i, current_section, "object", s, parsed))
            continue

        if INDEXED_REL_RE.match(stripped):
            parsed = _parse_indexed_relation(stripped)
            parsed["line_no"] = i
            relations.append(parsed)
            records.append(AHMRecord(i, current_section, "relation", s, parsed))
            continue

        km = KEY_ASSIGN_RE.match(stripped)
        if km:
            key, value = km.groups()
            if current_section == "KEY":
                keys[key] = value
                records.append(AHMRecord(i, current_section, "key", s, {"key": key, "value": value}))
            else:
                records.append(AHMRecord(i, current_section, "assignment", s, {
                    "key": key, "value": value
                }))
            continue

        dm = DIRECTIVE_RE.match(stripped)
        if dm:
            name, body = dm.groups()
            parsed = {"name": name, **_parse_directive_body(body)}
            rec = AHMRecord(i, current_section, "directive", s, parsed)
            records.append(rec)
            local_records.append(rec)
            continue

        rec = AHMRecord(i, current_section, "local_text", s, {"text": stripped})
        records.append(rec)
        local_records.append(rec)

    if objects:
        declared = set(objects)
        for rel in relations:
            src, tgt = rel.get("source"), rel.get("target")
            if src and src not in declared:
                warnings.append(
                    f"line {rel.get('line_no','?')}: relation source {src!r} is not a declared O: object "
                    f"(may be a valid local/external identifier)"
                )
            if tgt and tgt not in declared:
                warnings.append(
                    f"line {rel.get('line_no','?')}: relation target {tgt!r} is not a declared O: object "
                    f"(may be a valid local/external identifier)"
                )

    return AHMDocument(
        path=path,
        text=text,
        records=records,
        sections=sections,
        keys=keys,
        objects=objects,
        facts=facts,
        relations=relations,
        states=states,
        next_items=next_items,
        actions=actions,
        sources=sources,
        local_records=local_records,
        warnings=warnings,
    )


def parse_ahm_file(path: Path) -> AHMDocument:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValueError(f"{path}: not valid UTF-8: {e}") from e
    return parse_ahm_text(text, str(path))


def print_summary(doc: AHMDocument) -> None:
    s = doc.summary()
    print("AHM CORE PARSER")
    print(f"File: {s['path']}")
    print(f"Sections: {len(s['sections'])}")
    if s["sections"]:
        print("  " + " -> ".join(s["sections"]))
    print(f"Keys: {s['key_count']}")
    print(f"Objects: {s['object_count']}")
    print(f"Facts: {s['fact_count']}")
    print(f"Relations: {s['relation_count']}")
    print(f"States: {s['state_count']}")
    print(f"NEXT items: {s['next_count']}")
    print(f"Actions: {s['action_count']}")
    print(f"Sources: {s['source_count']}")
    print(f"Preserved local/unparsed constructs: {s['local_or_unparsed_count']}")
    print(f"Soft warnings: {s['warning_count']}")


def run_self_test() -> int:
    sample = """INSTRUCTIONS
Read KEY and continue the project.

KEY
O = OBJECT
F = FACT
R = RELATION
S = STATE
N = NEXT

MEMORY
O:BAT:Battery
O:CTRL:Controller
R:BAT>CTRL:POWERS
F:BAT:VOLTAGE=24V:V:SRC1
S:CTRL=INSTALLED
N:TEST_CTRL

LOCAL_EXTENSION
RELKEY.1:: FROM::{A} | TO::{B} | TYPE::CUSTOM
CUSTOM_RULE::AI_INTERPRETS_THIS
"""
    doc = parse_ahm_text(sample, "<self-test>")
    checks = [
        (len(doc.objects) == 2, "objects"),
        (len(doc.relations) == 1, "relations"),
        (len(doc.facts) == 1, "facts"),
        (len(doc.states) == 1, "states"),
        (doc.next_items == ["TEST_CTRL"], "next"),
        (doc.render() == sample, "lossless round-trip"),
        (any(r.parsed.get("name") == "RELKEY.1" for r in doc.local_records), "local extension preserved"),
    ]
    issues = soft_validate(doc)
    checks.append((not any(i.level == "ERROR" for i in issues), "soft validation"))

    failed = [name for ok, name in checks if not ok]
    if failed:
        print("SELF-TEST: FAIL")
        for name in failed:
            print(" -", name)
        return 1
    print("SELF-TEST: PASS")
    print("Core parsed, tolerant validation passed, local extensions preserved, exact text round-trip preserved.")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Tolerant parser for the self-describing AHM core.")
    ap.add_argument("file", nargs="?", type=Path)
    ap.add_argument("--json", action="store_true", help="Emit parsed structure as JSON.")
    ap.add_argument("--check", action="store_true", help="Show parser soft consistency warnings.")
    ap.add_argument("--validate", action="store_true",
                    help="Run tolerant Core validation. Unknown local constructs are preserved, not rejected.")
    ap.add_argument("--roundtrip-check", action="store_true",
                    help="Verify that parsing preserves the original decoded text exactly.")
    ap.add_argument("--self-test", action="store_true", help="Run built-in parser tests.")
    args = ap.parse_args(argv)

    if args.self_test:
        return run_self_test()

    if not args.file:
        ap.error("file is required unless --self-test is used")

    try:
        doc = parse_ahm_file(args.file)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(doc.to_jsonable(), ensure_ascii=False, indent=2))
    else:
        print_summary(doc)

    if args.check:
        if doc.warnings:
            print("\nSOFT WARNINGS")
            for w in doc.warnings:
                print("-", w)
        else:
            print("\nSOFT CHECK: no warnings")

    if args.validate:
        issues = soft_validate(doc)
        result = validation_result(issues)
        print(f"\nSOFT VALIDATION: {result}")
        for issue in issues:
            print(issue.render())
        if result == "FAIL":
            return 1

    if args.roundtrip_check:
        original = args.file.read_bytes().decode("utf-8-sig")
        if doc.render() == original:
            print("\nROUND-TRIP: PASS (decoded text preserved exactly)")
        else:
            print("\nROUND-TRIP: FAIL")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

