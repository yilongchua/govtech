# 07 - Evaluation And Reporting

## Evaluation Focus

Scenario 4 says the evaluation component is key. The system should evaluate both the exam paper and the AI pipeline.

## What To Evaluate

| Layer | Question |
|---|---|
| Document ingestion | Did we extract the correct pages, text, images, and metadata? |
| Exam structure | Did we identify all sections, questions, sources, marks, and choice groups? |
| Syllabus structure | Did we extract all assessment objectives, components, and examinable topics? |
| AI annotation | Did the model map each question to the right objective and topic? |
| Topic weightage | Did the system calculate candidate-required and offered marks correctly? |
| Report quality | Are findings clear, evidenced, and suitable for public consumption? |

## Gold Labels For History Paper 1

Use manually labelled gold data for the specimen paper.

| Item | Gold label |
|---|---|
| Total marks | 50 |
| Section A | 30 marks; source-based case study; AO1 + AO3 |
| Section B | candidate answers 2 of 3 essay questions; 20 marks; AO1 + AO2 |
| Q1 topic | Key developments leading to the outbreak of World War II in Europe; appeasement |
| Q2 topic | Extension of European control in Southeast Asia |
| Q3 topic | Treaty of Versailles and immediate impact on Germany |
| Q4 topic | Key developments leading to the outbreak of World War II in the Asia-Pacific |

## Metrics

| Metric | Definition |
|---|---|
| Extraction exact match | Percentage of fields that match the gold structure exactly. |
| Mark total accuracy | Whether section and paper totals match expected values. |
| AO classification accuracy | Percentage of questions with correct AO labels. |
| Topic top-1 accuracy | Percentage of questions whose selected syllabus topic matches gold. |
| Topic top-3 recall | Whether the correct topic appeared in the top 3 semantic candidates. |
| Evidence quality score | Human 1-5 rating of whether cited evidence supports the claim. |
| Issue detection quality | Whether expected warnings/errors are raised without stopping the pipeline. |

## Topic Weightage Reporting

Separate two ideas:

| View | Definition |
|---|---|
| Candidate-required marks | Marks every candidate must encounter. In Paper 1, Section A is compulsory, so Q1 contributes 30 required marks. |
| Offered marks | Marks available across the question menu. Section B offers more topics than a candidate answers. |

This distinction is critical for public communication. Otherwise the report may imply every candidate answers all essay questions.

## Public-Facing Data Story Output

Recommended sections:

1. **What the paper asks students to do.**
   Use a stacked bar for source-based vs essay marks.

2. **Which syllabus objectives are tested.**
   Use an AO heatmap by question.

3. **Which topics appear.**
   Use a topic coverage chart with candidate-required and offered marks.

4. **How confident the AI pipeline is.**
   Use a scorecard for extraction, classification, and evidence quality.

5. **What still needs human judgement.**
   Explain that AI can assist with structure and comparison, but assessment specialists should validate high-stakes conclusions.

## Structural Comparison Template

```markdown
## Structural Comparison With Syllabus

| Component | Expected From Syllabus | Observed In Paper | Status |
|---|---|---|---|
| Paper total | 50 marks | 50 marks | Pass |
| Section A | 30 marks, source-based | 30 marks, Q1(a)-Q1(e) | Pass |
| Section B | Answer 2 of 3 essays | 3 essay prompts, 10 marks each | Pass |
| Source count | Maximum 6 | 6 sources | Pass |

## Topic Weightage

| Topic | Required marks | Offered marks | Notes |
|---|---:|---:|---|
| Appeasement / WWII Europe | 30 | 30 | Compulsory source-based case study. |
| Colonial Southeast Asia | 0 | 10 | Offered through essay choice Q2. |
| Treaty of Versailles | 0 | 10 | Offered through essay choice Q3. |
| WWII Asia-Pacific | 0 | 10 | Offered through essay choice Q4. |
```

