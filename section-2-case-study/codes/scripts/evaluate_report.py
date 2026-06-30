#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a comparison report against the History Paper 1 gold fixture.")
    parser.add_argument("--report", required=True)
    parser.add_argument("--gold", default="tests/fixtures/history_2174_paper_1_gold.json")
    args = parser.parse_args()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    gold = json.loads(Path(args.gold).read_text(encoding="utf-8"))
    annotations = {item["question_id"]: item for item in report["annotations"]}
    topic_correct = 0
    objective_correct = 0
    total = len(gold["topics"])
    for qid, topic in gold["topics"].items():
        if annotations.get(qid, {}).get("predicted_topic") == topic:
            topic_correct += 1
        if annotations.get(qid, {}).get("predicted_objectives") == gold["objectives"][qid]:
            objective_correct += 1
    weightage = {item["topic"]: item for item in report["topic_weightage"]}
    weightage_correct = sum(
        1
        for topic, expected in gold["topic_weightage"].items()
        if topic in weightage
        and weightage[topic]["required_marks"] == expected["required_marks"]
        and weightage[topic]["offered_marks"] == expected["offered_marks"]
    )
    metrics = {
        "paper_total_match": report["exam_paper"]["total_marks"] == gold["total_marks"],
        "question_count_match": len(report["exam_paper"]["questions"]) == gold["question_count"],
        "source_count_match": len(report["exam_paper"]["sources"]) == gold["source_count"],
        "topic_top1_accuracy": topic_correct / total,
        "ao_accuracy": objective_correct / total,
        "topic_weightage_accuracy": weightage_correct / len(gold["topic_weightage"]),
    }
    print(json.dumps(metrics, indent=2))
    if not all(value == 1.0 or value is True for value in metrics.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
