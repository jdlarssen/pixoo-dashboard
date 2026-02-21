---
created: 2026-02-21T12:49:04.144Z
title: Replace ASCII approximations with Norwegian characters in README
area: docs
files:
  - README.md
---

## Problem

The README.md is written in Norwegian but uses ASCII approximations instead of actual Norwegian characters (æ, ø, å) throughout the entire file. Zero occurrences of æ, ø, or å found via grep.

Examples of current approximations:
- "Alltid-pa" should be "Alltid-på"
- "vaer" should be "vær"
- "a ta opp" should be "å ta opp"
- "gar" should be "går"
- "gronn" should be "grønn"
- "ae, oe og aa" should be "æ, ø og å"
- "Vaeranimasjonar" should use proper Norwegian spelling

This affects nearly every paragraph in the ~414-line README. The README explicitly claims Norwegian language but delivers ASCII-only text, which reads unnaturally to Norwegian speakers.

## Solution

Replace all ASCII approximations with proper Norwegian characters (æ, ø, å, Æ, Ø, Å) throughout README.md. Common substitutions:
- "ae" → "æ" (where it represents the Norwegian letter)
- "oe" → "ø" (where it represents the Norwegian letter)
- "aa" → "å" (where it represents the Norwegian letter)
- Standalone "a" used as infinitive marker → "å"
- Words like: vaer→vær, pa→på, gar→går, gronn→grønn, rod→rød, hoyde→høyde, etc.

Note: Cannot do blind find-replace — must be context-aware (e.g., "data" should NOT become "datå"). Manual review of each substitution needed.

User preference: use æ, ø, å where applicable. If there were a technical limitation preventing this, the README should be in English instead.
