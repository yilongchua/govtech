# Revamp Implementation Notes

Date: 2026-06-30

## Implemented

- Added a generic `run_analysis` workflow with subject-route resolution after first-page classification.
- Preserved History `2174` as `history_o_level_2174` and kept `run_history_analysis` as a compatibility alias.
- Added a `generic_exam_subject` route so non-History uploads no longer run through History-only rules.
- Added route-level syllabus loading, extraction, rule checks, annotation, and structure metrics.
- Replaced annotation confidence with `evidence_page_numbers`.
- Updated LLM exam extraction validation so every LLM-extracted source must include `page_number`.
- Updated fallback History extraction to attach page numbers to extracted questions and sources.
- Enabled LLM-backed question-to-syllabus annotation for non-mock model clients, with deterministic fallback.
- Generalized frontend copy, download names, structure rendering, Markdown export, DOCX export, and chart payloads.
- Added `GET /api/subjects` and made `/api/syllabus/latest` accept `subject_code`, returning configured History or generic unconfigured metadata.
- Added a non-History generic-route test.

## Remaining Production Work

The platform now supports routing all subjects through a generic fallback, but production-grade alignment for each subject still needs subject-specific syllabus assets and rule packs. The next route to add should define:

- syllabus PDF/Markdown/JSON assets;
- assessment objectives or learning outcomes;
- paper/component rules;
- mark and choice policies;
- subject-specific extraction hints;
- alignment evaluation expectations.

The current generic route is intentionally conservative: it preserves traceability and avoids applying History rules to unrelated subjects.
