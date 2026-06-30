# 02 - Frontend Experience

## User Flow

1. User opens the app.
2. The app waits for the user to provide an exam-paper PDF.
3. The backend identifies the subject route from the first page of the uploaded PDF.
4. User drags one or more PDF exam papers into a large upload area.
5. User clicks `Submit`.
6. The app shows a loading bar and stage-level status.
7. The app renders a structural comparison against the syllabus.

## First Screen Layout

The app should be an operational tool, not a marketing page.

```text
+-------------------------------------------------------------+
| Exam Paper Alignment Review                                  |
+-------------------------------------------------------------+
|                                                             |
|              +                                      |
|                                                             |
|        Drag and drop PDF exam papers here                   |
|                                                             |
|              [Submit]                                       |
|                                                             |
+-------------------------------------------------------------+
```

The MVP no longer exposes a year selector. The comparison baseline is selected by backend subject routing: uploaded exam paper -> first-page subject detection -> History syllabus for the current POC.

## Upload Rules

| Rule | Frontend behavior |
|---|---|
| Only PDFs accepted | Reject other file types before upload. |
| Input is always an exam paper | UI copy should say "Upload exam paper PDF". |
| First page must be the exam cover | The backend validates this; frontend shows warning if the sanity check fails. |
| Multiple files later, one file for MVP | MVP can support one file but design the API around job IDs and file IDs. |

## Loading Bar

The loading bar should reflect backend progress events:

| Stage | Example message |
|---|---|
| `uploaded` | Upload received. |
| `sanity_check` | Checking first page and exam-paper type. |
| `convert_pdf` | Converting PDF to Markdown and page images. |
| `extract_exam` | Extracting sections, questions, sources, and marks. |
| `load_syllabus` | Loading latest syllabus objectives. |
| `compare` | Comparing question structure with syllabus objectives and topic weightage. |
| `report` | Preparing structured report. |
| `complete` | Report ready. |

The loading bar should be determinate when the backend sends percentages. If a model call takes longer than expected, keep the bar moving at the stage level but show that the current step is still running.

## Output Report

The report should show:

| Section | Content |
|---|---|
| Document summary | Subject, paper code, paper title, exam year, duration, total marks. |
| Syllabus baseline | Syllabus year, subject, source URL, extracted objectives. |
| Structural comparison | Expected vs observed paper components and mark totals. |
| Objective alignment | Question-by-question AO mapping. |
| Topic weightage | Candidate-required marks and offered-question marks by topic. |
| Evidence table | Question prompt, marks, predicted topic, syllabus field, confidence. |
| Warnings and errors | Accumulated schema records with severity and evidence. |
| Export actions | Download JSON report and Markdown report. |

## Frontend API Calls

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/syllabus/latest` | Optional metadata endpoint for diagnostics; not used by the upload-first UI. |
| `POST` | `/api/uploads` | Upload one PDF and create a job. |
| `GET` | `/api/jobs/{job_id}` | Poll job status and progress. |
| `GET` | `/api/jobs/{job_id}/report` | Fetch final report JSON. |
