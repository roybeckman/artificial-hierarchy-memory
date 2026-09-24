# AHM 1.0 — Specification

**Artificial Hierarchy Memory (AHM)**  
Version: **1.0**  
Author: **Roy Beckman**  
Year: **2026**

## 1. Purpose

AHM is a self-describing structured plain-text language designed primarily for AI systems. Its primary purpose is semantic handoff and continuation: one AI should be able to receive an AHM file, understand the local structure and meaning, reconstruct the current state, and continue the work.

AHM is not intended to replace databases, JSON APIs, XML schemas, RDF systems, or deterministic machine-to-machine interchange formats.

**THE FILE TEACHES THE AI HOW TO READ THE FILE.**

## 2. Design model

**Structure guides the AI. Language carries the meaning.** AHM gives the AI a map instead of a wall of prose while preserving the meaning needed for reconstruction and continuation.

## 2A. Map principle

A capable AI receiving ordinary prose often has to perform orientation, structuring, and then reasoning or action. AHM encodes much of orientation and structuring directly through `DESCRIPTION`, `INSTRUCTIONS`, `KEY`, objects, facts, relations, status, `STATE`, `NEXT`, and validation.

**AHM removes the need for the AI to first build the map. The map is already there.**

This does not remove reasoning. It reduces unnecessary reconstruction before useful work begins.

## 3. Self-description

An AHM file SHOULD contain enough local information for a capable AI to determine what the file describes, how it should be read, what codes mean, which objects and relationships matter, what is current or uncertain, which validation rules apply, and what remains to be done.

Common mechanisms include `INSTRUCTIONS`, `DESCRIPTION`, `READ_ORDER`, `SPEC`, `FIELD_DICTIONARY`, `KEY`, `RELKEY`, `STATE`, `VALIDATION`, `NEXT`, and `INFORMATION_BANK`.

## 4. Common Core forms

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

A `KEY` section may define these or other local symbols. Domain extensions are valid when defined inside the file.

## 5. Epistemic discipline

Typical status markers include `V = VERIFIED`, `M = MEMORY_ONLY`, `U = UNRESOLVED`, `OLD = HISTORICAL_OR_SUPERSEDED`, and `CUR = CURRENT`. Unknown information should remain unknown rather than being invented.

## 6. Relations, state, and continuation

Important relationships SHOULD be explicit. `STATE` describes what is true now. `NEXT` describes what remains to be done. A project should continue from the state carried by the file rather than restart when the AI changes.

## 7. Local extensions and parser model

AHM permits local domain constructs such as `RELKEY`, indexes, research structures, and image-control constraints. A tolerant parser may extract common structures, but unknown local constructs MUST be preserved rather than rejected. The parser is optional tooling and is not required for basic AI understanding.

## 8. Success criterion

**Can a capable AI read one self-describing AHM file, understand it, and continue the work correctly?** If yes, the central AHM mechanism is functioning.

---

AHM 1.0 was created and developed by **Roy Beckman** in 2026.
