# How An AI Helper Can Read A History Exam Paper Without Losing The Plot

![Teachers reviewing AI exam analysis](assets/moe-teachers-ai-review-cartoon.png)

Imagine a very earnest teaching assistant who loves checklists. Give it a History exam paper, the latest syllabus, and a cup of digital kopi, and it tries to answer two practical questions:

1. Does this paper line up with the syllabus objectives?
2. Are the topics balanced in a way teachers can review?

That is what this prototype does for O-Level History Paper 1.

## The Small Classroom Problem

When teachers review an exam paper, the work is not just "does this look like History?" It is more precise:

- Are source-based questions testing the intended source skills?
- Are essay questions mapped to the right assessment objectives?
- Does one topic quietly dominate the marks?
- Can a reviewer trace each AI claim back to an exam page?

The prototype treats those as structured checks, not vibes.

## What The Pipeline Does

The current implementation has a React frontend and a FastAPI backend. The teacher-facing flow is simple: upload one or more PDF papers, choose the syllabus, and download a JSON or Word report.

Behind the scenes, the backend runs a more careful route:

1. Validate the PDF.
2. Render the first page.
3. Ask a local or mock model to identify the paper.
4. Convert the PDF into page-bounded Markdown.
5. Load the configured syllabus.
6. Extract questions, sources, marks, sections, and page numbers.
7. Map questions to syllabus objectives and topics.
8. Calculate topic weightage as both required marks and offered marks.
9. Export a traceable report with issues, rule checks, and evidence pages.

For History Paper 1, the important distinction is that Section A is compulsory, while Section B contains choices. So the report separates what every candidate must answer from what the paper offers.

## What The AI Is Allowed To Say

The prototype is intentionally strict. The AI does not get to produce a poetic verdict such as "this is a well-balanced paper".

Instead, it must produce structured fields:

- predicted assessment objectives, such as AO1, AO2, or AO3;
- predicted syllabus topic;
- evidence from the question;
- evidence page numbers;
- ambiguity notes when mapping is uncertain.

That matters because teachers should be able to ask, "Why did you say this?" and get a concrete answer.

## The Cute But Serious Bit: Evaluation

The evaluation component checks the AI/pipeline output against a reviewed reference answer set for the History Paper 1 specimen. It scores:

- exact-match accuracy;
- textual similarity;
- completeness;
- hallucination risk, by checking whether predicted values are supported by the paper text.

A stored deterministic reference run achieved perfect scores on 28 evaluated keys. A fresh mock-model run still extracted the paper correctly, with 50 marks and no pipeline issues, but returned `Uncertain` for topic/objective mapping. That is a useful result, not a failure of evaluation. It shows the difference between:

- the plumbing working;
- extraction working;
- the AI reasoning step being genuinely assessable.

In other words, the evaluation harness catches when the system cannot confidently map questions to syllabus topics. Good. We want that honesty.

## Can This Work For Other Subjects?

Yes, but not by magic.

The general shape can be reused: PDF ingestion, first-page routing, syllabus extraction, question extraction, alignment mapping, weightage calculation, and report generation.

But each subject needs its own rules. Mathematics may care about strands, cognitive demand, and calculator/non-calculator constraints. Science may care about practical skills and content domains. Literature may care about text coverage and response modes. Mother Tongue subjects may need language-specific extraction and oral/written component logic.

So the reusable part is the pipeline. The subject-specific part is the rule pack.

## Practical Use In Schools

The model can be self-hosted through LM Studio, Ollama, or an OpenAI-compatible local endpoint. That helps with data governance, cost control, and offline testing. The prototype also includes a mock provider so developers can test the pipeline without depending on model quality.

For real use, teachers should treat the report as a review assistant:

- use it to find imbalance quickly;
- use evidence pages to inspect claims;
- review all uncertain mappings;
- keep a human teacher as the final decision-maker.

The goal is not to replace professional judgment. It is to make the tedious first pass faster, more transparent, and easier to discuss.

## The Takeaway

The best part of this prototype is not that an AI can "read" an exam paper. It is that the system makes the AI show its working.

For teachers, that is the difference between a mysterious robot answer and a useful colleague with a very neat checklist.
