# Section 2 Case Study - Scenario 4

## Scenario

Design a pipeline to generate AI-based analysis of the O-Level History examination Paper 1, focusing on:

1. alignment with syllabus objectives;
2. balance of topic weightage;
3. evaluation of AI outputs;
4. whether the pipeline can generalise to other subjects;
5. real-world considerations for practical usage.

The recommended public-facing output should be a data story suitable for general public consumption, such as annotated charts, tables, and a blog-style write-up.

## Suggested Data Sources

| Source | Local file | Purpose |
|---|---|---|
| O-Level History syllabus, syllabus 2174 | `section-2-case-study/data/r-resources/2174_syllabus.pdf` and `.md` | Ground truth for assessment objectives, paper format, source-based case-study rules, examinable topics, and topic labels. |
| O-Level History specimen examination Paper 1 | `section-2-case-study/data/r-resources/2174_specimen_paper_1.pdf` and `.md` | Target document for the AI-based analysis. |
| O-Level History specimen examination Paper 2 | `section-2-case-study/data/r-resources/2174_specimen_paper_2.pdf` and `.md` | Optional comparator to test whether the pipeline generalises across the same subject. |
| Source repository | `section-2-case-study/data/r-resources/` | Cloned from `https://github.com/aipracticegovsg/r-resources.git`. |

The PDF files have been converted into Markdown in the same folder so that the analysis pipeline can work on inspectable text while retaining the original PDFs for audit.

## Concrete Understanding Of The Problem

The task is not simply to ask a model whether the paper is "good". A credible pipeline must produce traceable, structured claims that can be checked against the syllabus and exam paper. The core output should answer: "Does this specimen Paper 1 test what the syllabus says it should test, and is its topic coverage balanced enough for the public to understand?"

For Paper 1, the syllabus states that the paper has 50 marks:

| Component | Syllabus role | Marks | Assessment objectives |
|---|---:|---:|---|
| Section A: Source-Based Case Study | Compulsory source questions | 30 | AO1 + AO3 |
| Section B: Essays | Answer 2 out of 3 questions | 20 | AO1 + AO2 |

The specimen Paper 1 follows this format:

| Paper 1 part | Specimen question focus | Marks |
|---|---|---:|
| Section A Q1(a)-(e) | Appeasement towards Germany, with sources on Hitler, Chamberlain, Rothermere, the Czech crisis, a cartoon, and a later historical article | 30 |
| Section B Q2(a)/(b) | Dutch colonisation of Indonesia or French colonisation of Vietnam from the 1870s | 10 |
| Section B Q3 | German views of the Treaty of Versailles | 10 |
| Section B Q4 | US policy towards Japan and the outbreak of World War II in the Asia-Pacific | 10 |

This means the paper is structurally aligned at the component level: 60% source-based analysis and 40% essays for a candidate who answers the required number of questions. Topic balance needs more nuance. By offered questions, the paper exposes students to colonial Southeast Asia, post-World War I Europe, World War II in Europe, and World War II in the Asia-Pacific. By experienced marks, however, every candidate must spend 30 out of 50 marks on the appeasement case study, while their remaining 20 marks depend on essay choices.

## Proposed Data Story

Working title: **What Does One History Exam Paper Really Test?**

The story can be written for parents, students, and interested members of the public. It should avoid technical AI jargon in the main narrative and use visuals to show what the paper rewards.

1. **Start with the exam blueprint.**
   Show a 50-mark stacked bar: 30 marks source-based case study, 20 marks essays. Annotate that source interpretation and evaluation dominate the paper.

2. **Map each question to syllabus objectives.**
   Use a table or heatmap showing question, task verb, source requirement, marks, and likely AO mapping. For example, "How useful is this source..." maps strongly to AO3, while essay questions map to AO1 + AO2.

3. **Show topic coverage.**
   Use a topic treemap or bar chart. Separate "candidate-required marks" from "offered essay choices" so the public does not overread the three essay questions as all being answered.

4. **Explain the headline finding plainly.**
   A suitable public-facing finding: "The specimen paper follows the syllabus blueprint closely. Its strongest emphasis is not memorising every topic equally, but using historical knowledge to interpret sources and build arguments."

5. **End with what AI can and cannot do.**
   AI can rapidly tag questions, extract marks, compare them with syllabus rules, and draft explanations. Human review is still needed for syllabus interpretation, source-image handling, OCR errors, and defensible judgements about fairness or balance.

## Pipeline Design

### 1. Ingest And Normalise Documents

Inputs:

| Input | Processing |
|---|---|
| Syllabus PDF | Extract text to Markdown; segment into assessment objectives, scheme of assessment, syllabus content, and topic details. |
| Specimen Paper 1 PDF | Extract text to Markdown; segment into paper metadata, instructions, Section A, sources, sub-questions, and Section B essays. |
| Optional Paper 2 PDF | Run through the same workflow as a generalisation test. |

Output should be structured JSON or parquet tables, not only prose. Suggested entities:

| Entity | Fields |
|---|---|
| `assessment_objective` | `ao_id`, `description`, `skills`, `source_page` |
| `syllabus_topic` | `paper`, `unit`, `topic`, `is_source_based_eligible`, `key_concepts`, `source_page` |
| `exam_question` | `paper`, `section`, `question_id`, `prompt`, `marks`, `required_sources`, `choice_group` |
| `source_item` | `source_id`, `source_type`, `attribution`, `date`, `word_count`, `linked_question_ids` |
| `ai_annotation` | `question_id`, `predicted_ao`, `predicted_topic`, `rationale`, `confidence`, `model_name`, `prompt_version` |

### 2. Rule-Based Baseline

Before using an LLM, build deterministic checks:

| Check | Expected Paper 1 rule |
|---|---|
| Total marks | 50 |
| Section A marks | 30 |
| Section B marks answered by candidate | 20 |
| Source-based sub-questions | Q1(a)-Q1(e) |
| Maximum number of sources | 6 |
| Essay questions | answer 2 out of 3 |
| Essay mark value | 10 marks each |

This baseline catches obvious errors and gives the AI less room to hallucinate.

### 3. AI Annotation Layer

Use an LLM to classify each question against syllabus content and assessment objectives. The prompt should force evidence-based output:

| Required AI output | Why it matters |
|---|---|
| predicted assessment objective | Shows alignment with AO1, AO2, AO3. |
| predicted syllabus topic | Supports topic-weightage analysis. |
| evidence quote from paper | Keeps the model grounded. |
| evidence quote or page reference from syllabus | Makes the claim auditable. |
| confidence and ambiguity flag | Helps identify where human review is needed. |

For example, the model should classify Q1(a) "How useful is this source..." as AO1 + AO3 because it requires source utility, contextual knowledge, and evaluation. It should classify Section B essays as AO1 + AO2 because they ask students to explain, evaluate, and make a judgement.

### 4. Evaluation Layer

The evaluation component is the key part of the case study. It should evaluate the AI output at three levels:

| Evaluation level | Method | Example metric |
|---|---|---|
| Extraction accuracy | Compare extracted marks, question IDs, source count, and section labels against manually checked gold labels. | exact-match accuracy; count mismatch rate |
| Classification accuracy | Compare AI AO/topic labels against a small human-labelled answer key. | precision/recall/F1 by label |
| Explanation quality | Human rubric checks whether the AI rationale cites correct evidence and avoids overclaiming. | 1-5 rubric score |

Minimum recommended gold set:

| Item | Gold label |
|---|---|
| Q1(a)-Q1(e) | AO1 + AO3; source-based; 30 marks total |
| Q2(a)/(b), Q3, Q4 | AO1 + AO2; essay; 10 marks each |
| Q1 topic | Key developments leading to the outbreak of World War II in Europe, especially appeasement |
| Q2 topic | Extension of European control in Southeast Asia |
| Q3 topic | Treaty of Versailles and immediate impact on Germany |
| Q4 topic | Key developments leading to the outbreak of World War II in the Asia-Pacific |

Evaluation should also include stress tests:

| Stress test | Risk being tested |
|---|---|
| Run on Paper 2 without changing prompts | Whether the pipeline generalises within History. |
| Remove section headers from the input | Overdependence on formatting. |
| Use OCR-noisy text | Robustness to scanned papers. |
| Ask model for citations | Whether evidence is grounded or fabricated. |
| Ask model to produce topic-weight charts from JSON only | Whether chart values stay consistent with extracted marks. |

### 5. Visualisation Layer

Recommended visuals:

| Visual | Data needed | Message |
|---|---|---|
| 50-mark stacked bar | section mark totals | Paper 1 prioritises source analysis. |
| AO heatmap by question | question-to-AO labels | Questions align with the stated assessment objectives. |
| Topic coverage bar chart | question-to-topic labels and marks | The paper covers multiple syllabus areas, with compulsory emphasis on appeasement. |
| AI evaluation scorecard | extraction and classification metrics | The pipeline is only useful if outputs are measured. |
| Human-in-the-loop workflow diagram | pipeline stages | AI assists analysis; humans approve final judgements. |

## Preliminary Findings From The Specimen Paper

| Finding | Evidence | Interpretation |
|---|---|---|
| Component-level alignment is strong. | The syllabus specifies 30 marks for source-based questions and 20 marks for essays; the specimen Paper 1 follows this. | The paper matches the published assessment format. |
| AO alignment is plausible. | Q1 asks students to evaluate usefulness, purpose, proof, agreement, and support across sources. | These are AO3-heavy tasks with AO1 contextual knowledge. |
| Essay questions align with AO1 + AO2. | Section B asks "How far do you agree..." across historical causes and explanations. | The prompts require knowledge, analysis, evaluation, and judgement. |
| The compulsory topic emphasis is concentrated. | Q1 allocates 30 marks to appeasement/Germany before World War II. | A candidate must spend 60% of Paper 1 marks on one source-based case study topic. |
| Offered topic coverage is broader than candidate-experienced coverage. | Section B offers colonial Southeast Asia, Treaty of Versailles, and Asia-Pacific war causes, but candidates answer two. | Public communication should distinguish between the paper's menu of questions and what any one candidate answers. |

## Generalisation To Other Subjects

The same pipeline can generalise when the subject has a published syllabus, assessment objectives, mark scheme, and structured exam papers. It is strongest for subjects where question intent can be inferred from command words and marks, such as Humanities and Social Sciences.

Generalisation requirements:

| Requirement | Why |
|---|---|
| Subject-specific ontology | "Topic", "skill", and "objective" mean different things across subjects. |
| Subject-specific command-word dictionary | "Evaluate" in History differs from "evaluate" in Science or Mathematics. |
| Human-labelled validation set | Needed to evaluate AI output rather than merely generate it. |
| Document-layout handling | Tables, diagrams, maps, and images must be extracted or represented accurately. |
| Clear policy on acceptable use | Exam analysis can inform curriculum review but should not become an opaque grading or ranking tool. |

For Mathematics or Science, the pipeline would need stronger diagram/table parsing and answer-step reasoning. For Languages, it would need rubric-aware analysis of comprehension, writing, and oral components. For Art or Design subjects, image and multimodal evaluation would become central.

## Real-World Usage Considerations

| Consideration | Practical implication |
|---|---|
| Model choice | A self-hosted model can be acceptable for classification and summarisation if quality is evaluated; high-stakes decisions require human approval. |
| Data sensitivity | Public exam papers and syllabuses are low-risk, but future live papers or internal moderation notes may require restricted processing. |
| Copyright | Store source PDFs for internal analysis; public outputs should quote sparingly and rely on summaries, extracted marks, and derived charts. |
| Traceability | Every AI claim should link back to a question ID, syllabus section, page, or extracted quote. |
| Reproducibility | Save prompts, model versions, extraction code, and evaluation labels. |
| Human review | Curriculum or assessment specialists should validate topic mappings and final interpretations. |
| Failure modes | Watch for hallucinated syllabus topics, wrong mark totals, missed OR questions, and incorrect treatment of image-based sources such as cartoons. |

## Recommended Next Steps

1. Build a small notebook in `section-2-case-study/codes/` that parses the Markdown files into question/source/topic tables.
2. Create a manually labelled answer key for Paper 1.
3. Run at least two model/prompt variants and compare them against the answer key.
4. Produce four public-facing charts: marks by section, AO heatmap, topic coverage, and AI evaluation scorecard.
5. Draft the final blog-style data story and convert the key visuals into presentation slides.
