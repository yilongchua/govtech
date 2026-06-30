from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from backend.app.core.config import settings
from backend.app.core.storage import read_json
from backend.app.schemas.comparison import QuestionAnnotation, RuleCheckResult, StructureMetric
from backend.app.schemas.exam import ExamPaper, FirstPageCheck
from backend.app.schemas.syllabus import SyllabusDocument
from backend.app.src.comparison.rule_checks import run_generic_paper_rules
from backend.app.src.comparison.semantic_matcher import annotate_question
from backend.app.src.extraction.llm_exam_extractor import extract_exam_with_llm, extract_history_exam_with_llm
from backend.app.src.ingestion.model_client import LLMClient


class SubjectRoute(Protocol):
    route_id: str
    subject_label: str

    def load_syllabus(self, first_page: FirstPageCheck) -> SyllabusDocument: ...

    def extract_exam(
        self,
        markdown_path: Path,
        pdf_path: Path,
        first_page: FirstPageCheck,
        syllabus: SyllabusDocument,
        client: LLMClient,
    ) -> tuple[ExamPaper, dict]: ...

    def run_rules(self, exam: ExamPaper, syllabus: SyllabusDocument) -> tuple[list[RuleCheckResult], list]: ...

    def annotate(self, exam: ExamPaper, syllabus: SyllabusDocument, client: LLMClient) -> list[QuestionAnnotation]: ...

    def structure_metrics(self, exam: ExamPaper, syllabus: SyllabusDocument) -> list[StructureMetric]: ...


@dataclass(frozen=True)
class RouteConfig:
    route_id: str
    subject: str
    subject_code: str
    year: int
    syllabus_json_path: Path
    extraction_profile: str = "generic"
    configured: bool = True


@dataclass(frozen=True)
class RouteResolution:
    status: str
    reason: str
    route: SubjectRoute | None = None
    candidates: list[dict] | None = None


@dataclass(frozen=True)
class GenericSubjectRoute:
    route_id: str = "generic_exam_subject"
    subject_label: str = "General Subject"
    route_config: RouteConfig | None = None

    def load_syllabus(self, first_page: FirstPageCheck) -> SyllabusDocument:
        if self.route_config is None:
            raise ValueError("No configured subject route is available.")
        return SyllabusDocument(**read_json(self.route_config.syllabus_json_path))

    def extract_exam(
        self,
        markdown_path: Path,
        pdf_path: Path,
        first_page: FirstPageCheck,
        syllabus: SyllabusDocument,
        client: LLMClient,
    ) -> tuple[ExamPaper, dict]:
        fallback_subject = self.route_config.extraction_profile if self.route_config else "generic"
        if fallback_subject == "history":
            return extract_history_exam_with_llm(markdown_path, pdf_path, first_page, syllabus, client)
        return extract_exam_with_llm(markdown_path, pdf_path, first_page, syllabus, client, fallback_subject="generic")

    def run_rules(self, exam: ExamPaper, syllabus: SyllabusDocument) -> tuple[list[RuleCheckResult], list]:
        return run_generic_paper_rules(exam, syllabus)

    def annotate(self, exam: ExamPaper, syllabus: SyllabusDocument, client: LLMClient) -> list[QuestionAnnotation]:
        return [
            annotate_question(question, syllabus, exam.paper_code, client, exam.sources, exam.questions)
            for question in exam.questions
        ]

    def structure_metrics(self, exam: ExamPaper, syllabus: SyllabusDocument) -> list[StructureMetric]:
        section_labels = sorted({q.section for q in exam.questions})
        metrics = [
            StructureMetric(label="Subject", value=exam.subject or "Unknown"),
            StructureMetric(label="Total marks", value=exam.total_marks),
            StructureMetric(label="Question count", value=len(exam.questions)),
            StructureMetric(label="Source count", value=len(exam.sources)),
        ]
        metrics.extend(
            StructureMetric(label=f"{section} marks", value=sum(q.marks or 0 for q in exam.questions if q.section == section))
            for section in section_labels
        )
        return metrics


def resolve_subject_route(first_page: FirstPageCheck, selected_subject_code: str | None = None) -> SubjectRoute:
    resolution = resolve_subject_route_with_status(first_page, selected_subject_code=selected_subject_code)
    if resolution.route is None:
        raise ValueError(resolution.reason)
    return resolution.route


def resolve_subject_route_with_status(first_page: FirstPageCheck, selected_subject_code: str | None = None) -> RouteResolution:
    if not first_page.is_exam_paper:
        return RouteResolution(
            status="uncertain",
            reason="first_page_not_exam_paper",
            candidates=[],
        )
    configs = _load_route_configs()
    if selected_subject_code:
        selected = next((config for config in configs if config.subject_code == selected_subject_code), None)
        if selected is None:
            return RouteResolution(
                status="unsupported",
                reason="selected_syllabus_not_found",
                candidates=[{"subject_code": selected_subject_code, "configured": False}],
            )
        candidates = [
            {
                "route_id": selected.route_id,
                "subject": selected.subject,
                "subject_code": selected.subject_code,
                "score": 1.0,
                "reasons": ["user_selected_syllabus"],
                "configured": selected.configured and selected.syllabus_json_path.exists(),
            }
        ]
        if not selected.configured or not selected.syllabus_json_path.exists():
            return RouteResolution(status="unsupported", reason="selected_syllabus_is_not_configured", candidates=candidates)
        syllabus = SyllabusDocument(**read_json(selected.syllabus_json_path))
        if not syllabus.objectives or not syllabus.components or not syllabus.topics:
            return RouteResolution(status="unsupported", reason="selected_syllabus_requirements_incomplete", candidates=candidates)
        return RouteResolution(
            status="ready",
            reason="selected_syllabus_route",
            route=GenericSubjectRoute(route_id=selected.route_id, subject_label=selected.subject, route_config=selected),
            candidates=candidates,
        )
    candidates = _score_route_candidates(first_page, configs)
    if not candidates:
        return RouteResolution(
            status="unsupported",
            reason="no_configured_route_for_detected_subject",
            candidates=[],
        )
    candidates.sort(key=lambda item: item["score"], reverse=True)
    best = candidates[0]
    if len(candidates) > 1 and best["score"] == candidates[1]["score"]:
        return RouteResolution(status="uncertain", reason="multiple_route_candidates_tied", candidates=candidates)
    if best["score"] < 0.75:
        return RouteResolution(status="uncertain", reason="route_match_confidence_too_low", candidates=candidates)
    config = next(config for config in configs if config.route_id == best["route_id"])
    if not config.configured or not config.syllabus_json_path.exists():
        return RouteResolution(status="unsupported", reason="matched_route_is_not_configured", candidates=candidates)
    syllabus = SyllabusDocument(**read_json(config.syllabus_json_path))
    if not syllabus.objectives or not syllabus.components or not syllabus.topics:
        return RouteResolution(status="unsupported", reason="matched_route_syllabus_is_incomplete", candidates=candidates)
    route = GenericSubjectRoute(
        route_id=config.route_id,
        subject_label=config.subject,
        route_config=config,
    )
    return RouteResolution(status="ready", reason="configured_route_matched", route=route, candidates=candidates)


def _load_route_configs() -> list[RouteConfig]:
    index_path = settings.data_dir / "reference" / "syllabus_index.json"
    if not index_path.exists():
        return []
    index = read_json(index_path)
    configs = []
    for item in index.get("syllabuses", []):
        subject_code = str(item.get("subject_code") or "").strip()
        json_path = Path(str(item.get("json_path") or ""))
        if json_path and not json_path.is_absolute():
            json_path = settings.root_dir / json_path
        if not subject_code or not json_path:
            continue
        configs.append(
            RouteConfig(
                route_id=f"configured_subject_{subject_code}_{item.get('year', settings.history_syllabus_year)}",
                subject=str(item.get("subject") or subject_code),
                subject_code=subject_code,
                year=int(item.get("year") or settings.history_syllabus_year),
                syllabus_json_path=json_path,
                extraction_profile="history" if subject_code == "2174" else "generic",
                configured=bool(item.get("json_path")),
            )
        )
    return configs


def _score_route_candidates(first_page: FirstPageCheck, configs: list[RouteConfig]) -> list[dict]:
    subject = (first_page.subject or "").strip().lower()
    subject_code = _subject_code(first_page)
    candidates = []
    for config in configs:
        score = 0.0
        reasons = []
        if subject_code and subject_code == config.subject_code:
            score += 0.7
            reasons.append("subject_code_matched")
        if subject and subject == config.subject.lower():
            score += 0.3
            reasons.append("subject_name_matched")
        elif subject and subject in config.subject.lower():
            score += 0.15
            reasons.append("subject_name_partially_matched")
        if not reasons:
            continue
        candidates.append(
            {
                "route_id": config.route_id,
                "subject": config.subject,
                "subject_code": config.subject_code,
                "score": min(score, 1.0),
                "reasons": reasons,
                "configured": config.configured and config.syllabus_json_path.exists(),
            }
        )
    return candidates


def _effective_offered_marks(questions) -> int:
    total = 0
    grouped: dict[str, int] = {}
    for question in questions:
        marks = question.marks or 0
        if question.choice_group:
            grouped[question.choice_group] = max(grouped.get(question.choice_group, 0), marks)
        else:
            total += marks
    return total + sum(grouped.values())


def _subject_code(first_page: FirstPageCheck) -> str:
    paper_code = first_page.paper_code or ""
    return paper_code.split("/")[0] if "/" in paper_code else paper_code or "unknown"
