# Section 2 Scenario 4 - Implementation Plan

This folder describes how to turn the Scenario 4 analysis into a production-style application for comparing uploaded exam papers against the most recent syllabus objectives and topic weightage.

## Goal

Build a pipeline that accepts exam-paper PDFs, verifies that they look like valid examination papers, extracts their structure, compares them against the relevant syllabus, and returns an auditable report on:

1. alignment with syllabus objectives;
2. balance of topic weightage;
3. extraction and model confidence;
4. accumulated warnings and errors;
5. structured evidence that can be reused for charts, tables, and a public-facing data story.

## Plan Files

| File | Purpose |
|---|---|
| `01_repo_structure.md` | Proposed production repository layout, including frontend, backend, Docker, dependencies, data, and tests. |
| `02_frontend_experience.md` | Upload UI, most-recent-year selector, loading states, and output report experience. |
| `03_backend_pipeline.md` | End-to-end backend flow from upload to final structural comparison. |
| `04_ingestion_and_syllabus_refresh.md` | PDF-only ingestion, vision sanity checks, PDF-to-Markdown conversion, and SEAB syllabus scraping for the current link. |
| `05_schema_design.md` | Pydantic-style schema plan for raw extraction, structured exam paper output, syllabus objectives, rule checks, and accumulated errors. |
| `06_prompts_and_langgraph.md` | LangGraph backbone, prompt responsibilities, local Qwen vision model usage, and extraction routing by subject/topic. |
| `07_evaluation_and_reporting.md` | Evaluation plan for AI annotations, rule checks, semantic comparison, and the public-facing data story. |
| `08_implementation_phases.md` | Suggested build sequence from MVP to production hardening. |

## Current Local Inputs

| Artifact | Path |
|---|---|
| Scenario 4 note | `section-2-case-study/DS Case Study Prod - Section 2 Scenario 4.md` |
| Downloaded 2026 History syllabus PDF | `section-2-case-study/2174_y26_sy.pdf` |
| Converted 2026 History syllabus Markdown | `section-2-case-study/2174_y26_sy.md` |
| Specimen Paper 1 PDF | `section-2-case-study/data/raw/exam_pdfs/2174_specimen_paper_1.pdf` |
| Specimen Paper 2 PDF | `section-2-case-study/data/raw/exam_pdfs/2174_specimen_paper_2.pdf` |

## Critical Design Choice

The system should not fail fast when the uploaded paper differs from expected rules. In production, invalid or surprising documents are useful signals. Rule failures should be accumulated into an error/warning schema with reasons, severity, and evidence, then shown in the report.
