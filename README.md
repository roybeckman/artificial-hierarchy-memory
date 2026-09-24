# AHM — Artificial Hierarchy Memory

**AHM 1.0**  
Created by **Roy Beckman** in 2026.

> **AHM provides the map. The AI does the work.**

> **The file teaches the AI how to read the file.**

Artificial Hierarchy Memory (AHM) is a self-describing, AI-native plain-text format for structured context, semantic handoff, project continuation, reasoning maps, state, relations, uncertainty, and AI control.

AHM gives a capable AI a map of the information instead of a wall of prose. Structure guides the AI; language carries the meaning.

## Why AHM exists

When an AI receives ordinary prose, it often has to reconstruct orientation and information structure before it can solve the actual task. AHM encodes much of that map in advance through descriptions, instructions, keys, objects, facts, relations, state, next actions, and validation.

The AI still interprets and reasons. AHM reduces unnecessary structural reconstruction before useful work can begin.

## AI-native documentation

Read [`THE_AHM_LANGUAGE.txt`](./THE_AHM_LANGUAGE.txt) to understand AHM 1.0 and use the format. The file is intended to teach the AI how to read AHM.

## Common pattern

```text
INSTRUCTIONS
DESCRIPTION
KEY
MEMORY / DOMAIN_DATA
RELATIONS
STATE
NEXT
INFORMATION_BANK
VALIDATION
```

AHM also supports data-only, reasoning, research, and image-control files. The file defines the local language it needs.

## Common compact records

```text
P:PROJECT_ID
O:OBJECT_ID:LABEL
F:SUBJECT:PROPERTY=VALUE[:TAG...]
R:SOURCE>TARGET:RELATION_TYPE[:TAG...]
S:SUBJECT=STATE
N:NEXT_ACTION
K:KNOWLEDGE_STATEMENT
A:ACTION
```

These are common Core forms, not a rigid universal schema. Domain-specific constructs are allowed when the file explains them.

## Examples

- [`examples/minimal_project.ahm`](./examples/minimal_project.ahm) — project continuation and state
- [`examples/data_only.ahm`](./examples/data_only.ahm) — scientific data and local dictionaries
- [`examples/reasoning.ahm`](./examples/reasoning.ahm) — reasoning structure and status hierarchy
- [`examples/image_control.ahm`](./examples/image_control.ahm) — image-AI structural control

## Optional parser

[`ahm_core_parser.py`](./ahm_core_parser.py) is a tolerant parser and soft validator. Its rule is:

> **Parse the core. Preserve the rest. Let the AI interpret local semantics.**

```bash
python ahm_core_parser.py examples/minimal_project.ahm --validate
python ahm_core_parser.py --self-test
```

No third-party Python packages are required.

## Files

- [`SPECIFICATION.md`](./SPECIFICATION.md)
- [`THE_AHM_LANGUAGE.txt`](./THE_AHM_LANGUAGE.txt)
- [`AHM_1.0_MAP_SKELETON_TEMPLATE.txt`](./AHM_1.0_MAP_SKELETON_TEMPLATE.txt)
- [`ahm_core_parser.py`](./ahm_core_parser.py)
- [`examples/`](./examples/)
- [`HISTORY.md`](./HISTORY.md)
- [`LICENSE.md`](./LICENSE.md)
- [`CITATION.cff`](./CITATION.cff)

## Origin and history

AHM was created and developed by **Roy Beckman** in 2026. The original June 2026 public revision is preserved under [`history/`](./history/) and remains part of the project's provenance.

## License

Current AHM 1.0 documentation, specification, reference text, README, map template, and examples are licensed under **CC BY 4.0**. The Python parser is licensed under the **MIT License**. See [`LICENSE.md`](./LICENSE.md).

---

**AHM 1.0 — Artificial Hierarchy Memory**  
**Roy Beckman · 2026**
