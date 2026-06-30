from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "diagrams"
OUT.mkdir(parents=True, exist_ok=True)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


TITLE = font(28, True)
BODY = font(16)
BODY_BOLD = font(16, True)
SMALL = font(13)


def wrap(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        next_line = f"{line} {word}".strip()
        if len(next_line) > max_chars and line:
            lines.append(line)
            line = word
        else:
            line = next_line
    if line:
        lines.append(line)
    return lines


def box(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], title: str, body: str = "", fill: str = "#ffffff") -> None:
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=10, fill=fill, outline="#334155", width=2)
    draw.text((x1 + 16, y1 + 12), title, font=BODY_BOLD, fill="#0f172a")
    if body:
        y = y1 + 42
        for line in wrap(body, max(18, (x2 - x1) // 9)):
            draw.text((x1 + 16, y), line, font=SMALL, fill="#475569")
            y += 18


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], label: str = "") -> None:
    draw.line([start, end], fill="#0f172a", width=3)
    sx, sy = start
    ex, ey = end
    if ex >= sx:
        points = [(ex, ey), (ex - 10, ey - 6), (ex - 10, ey + 6)]
    else:
        points = [(ex, ey), (ex + 10, ey - 6), (ex + 10, ey + 6)]
    draw.polygon(points, fill="#0f172a")
    if label:
        mx = (sx + ex) // 2
        my = (sy + ey) // 2 - 22
        draw.text((mx - len(label) * 3, my), label, font=SMALL, fill="#0f172a")


def canvas(title: str, size: tuple[int, int] = (1400, 900)) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", size, "#f8fafc")
    draw = ImageDraw.Draw(img)
    draw.text((40, 28), title, font=TITLE, fill="#0f172a")
    draw.line([(40, 72), (size[0] - 40, 72)], fill="#cbd5e1", width=2)
    return img, draw


def system_architecture() -> None:
    img, draw = canvas("System Architecture - History Exam Paper Alignment")
    box(draw, (70, 130, 350, 260), "React Frontend", "Latest year selector, PDF dropzone, submit button, progress bar, populated report tables.", "#e0f2fe")
    box(draw, (500, 130, 820, 260), "FastAPI Backend", "Upload endpoint, health endpoint, syllabus metadata endpoint, synchronous MVP job execution.", "#dcfce7")
    box(draw, (980, 130, 1300, 260), "Local Model Endpoint", "LM Studio OpenAI-compatible or Ollama. Used for first-page vision sanity check.", "#fef3c7")

    box(draw, (70, 420, 350, 560), "Data Volume", "raw/uploads, raw/exam_pdfs, processed/markdown, processed/json, processed/images.", "#f1f5f9")
    box(draw, (500, 420, 820, 560), "History Pipeline", "PDF guard, first-page render, Markdown conversion, syllabus extraction, exam extraction, checks, comparison.", "#ede9fe")
    box(draw, (980, 420, 1300, 560), "Report JSON", "Syllabus objectives, exam questions, rule checks, annotations, topic weightage, issues.", "#fee2e2")

    box(draw, (500, 680, 820, 800), "Docker Compose", "backend:8000 and frontend:5173. Model remains an external local service.", "#ffffff")

    arrow(draw, (350, 195), (500, 195), "POST /api/uploads")
    arrow(draw, (820, 195), (980, 195), "vision prompt")
    arrow(draw, (660, 260), (660, 420), "workflow")
    arrow(draw, (500, 490), (350, 490), "persist")
    arrow(draw, (820, 490), (980, 490), "build")
    arrow(draw, (980, 560), (350, 260), "render report")
    arrow(draw, (660, 680), (660, 560), "runs")

    img.save(OUT / "system_architecture.png")


def frontend_flow() -> None:
    img, draw = canvas("Frontend Populated Flow")
    box(draw, (60, 120, 380, 240), "Initial Load", "No syllabus dropdown. User starts by providing an exam-paper PDF.", "#e0f2fe")
    box(draw, (530, 120, 860, 240), "Populated Header", "Title: History Exam Paper Alignment. Subtitle explains first-page subject routing and History POC scope.", "#e0f2fe")
    box(draw, (1010, 120, 1340, 240), "Upload Workspace", "Huge plus icon, drag-and-drop PDF area, selected file name, Submit button.", "#e0f2fe")

    box(draw, (60, 390, 380, 530), "Submit State", "Progress starts at 15 percent Uploading, then 35 percent Analysing History paper.", "#dcfce7")
    box(draw, (530, 390, 860, 530), "Backend Response", "status=complete, progress=100, stage=complete, report object attached.", "#dcfce7")
    box(draw, (1010, 390, 1340, 530), "Report UI", "Summary cards: Paper, Syllabus, Marks. Tables: Structural Comparison, Topic Weightage, Objective Alignment, Warnings.", "#dcfce7")

    box(draw, (315, 680, 1085, 805), "Visible Populated Information", "Detected paper code/title/subject, syllabus subject/code/year, total marks, rule pass/review status, required/offered topic marks, AO labels and confidence, issue list.", "#ffffff")

    arrow(draw, (380, 180), (530, 180), "state")
    arrow(draw, (860, 180), (1010, 180), "user selects PDF")
    arrow(draw, (1175, 240), (220, 390), "submit")
    arrow(draw, (380, 460), (530, 460), "POST")
    arrow(draw, (860, 460), (1010, 460), "render")
    arrow(draw, (1175, 530), (700, 680), "fields")

    img.save(OUT / "frontend_flow.png")


def backend_pipeline() -> None:
    img, draw = canvas("Backend End-To-End Pipeline")
    boxes = [
        ((50, 130, 280, 245), "1. PDF Upload", "FastAPI accepts PDF only and creates job_id."),
        ((360, 130, 590, 245), "2. PDF Guard", "Extension, parser readability, page count."),
        ((670, 130, 900, 245), "3. First Page", "Render cover page PNG with PyMuPDF."),
        ((980, 130, 1210, 245), "4. Vision Check", "Local model classifies exam cover, subject, paper code."),
        ((50, 370, 280, 485), "5. Markdown", "Convert PDF pages to Markdown with page boundaries."),
        ((360, 370, 590, 485), "6. Syllabus", "Load 2174_y26_sy.md and extract AO/component/topic schema."),
        ((670, 370, 900, 485), "7. Exam Extract", "Extract sources, questions, marks, sections, choice groups."),
        ((980, 370, 1210, 485), "8. Rules", "Accumulate issues instead of failing fast."),
        ((360, 610, 590, 725), "9. Annotation", "Map each question to AO and syllabus topic."),
        ((670, 610, 900, 725), "10. Weightage", "Separate required marks from offered choice marks."),
        ((980, 610, 1210, 725), "11. Report", "Persist comparison_report.json and return to frontend."),
    ]
    for xy, title, body in boxes:
        box(draw, xy, title, body, "#ffffff")
    for start, end in [
        ((280, 188), (360, 188)),
        ((590, 188), (670, 188)),
        ((900, 188), (980, 188)),
        ((1095, 245), (165, 370)),
        ((280, 428), (360, 428)),
        ((590, 428), (670, 428)),
        ((900, 428), (980, 428)),
        ((1095, 485), (475, 610)),
        ((590, 668), (670, 668)),
        ((900, 668), (980, 668)),
    ]:
        arrow(draw, start, end)
    img.save(OUT / "backend_pipeline.png")


def local_model_testing() -> None:
    img, draw = canvas("Local Model Testing Flow")
    box(draw, (70, 130, 390, 260), "Test Script", "scripts/run_e2e_local_model_test.py accepts PDF, provider, base URL, model, and --require-real-model.", "#e0f2fe")
    box(draw, (540, 90, 860, 220), "Mock Provider", "Deterministic local run. No model service required. Useful for CI and schema checks.", "#dcfce7")
    box(draw, (540, 300, 860, 430), "LM Studio", "OpenAI-compatible /v1/models preflight, then vision chat completion request.", "#fef3c7")
    box(draw, (540, 510, 860, 640), "Ollama", "/api/tags preflight, then /api/generate vision request. Cleanly fails if endpoint is absent.", "#fee2e2")
    box(draw, (1010, 300, 1320, 430), "Same Pipeline", "All providers feed the same first-page check and report-generation workflow.", "#ffffff")

    arrow(draw, (390, 195), (540, 155), "provider=mock")
    arrow(draw, (390, 195), (540, 365), "provider=openai-compatible")
    arrow(draw, (390, 195), (540, 575), "provider=ollama")
    arrow(draw, (860, 155), (1010, 340), "check")
    arrow(draw, (860, 365), (1010, 365), "check")
    arrow(draw, (860, 575), (1010, 390), "check")

    img.save(OUT / "local_model_testing.png")


def data_contracts() -> None:
    img, draw = canvas("Data Contracts And Report Payload")
    box(draw, (70, 130, 360, 270), "SyllabusDocument", "subject, subject_code, year, objectives, components, topics, issues.", "#ede9fe")
    box(draw, (555, 130, 845, 270), "ExamPaper", "subject, paper_code, paper_title, total_marks, sources, questions, issues.", "#ede9fe")
    box(draw, (1040, 130, 1330, 270), "QuestionAnnotation", "question_id, predicted_objectives, predicted_topic, evidence, confidence.", "#ede9fe")
    box(draw, (315, 460, 605, 600), "RuleCheckResult", "rule_id, expected, observed, passed, severity_if_failed.", "#f1f5f9")
    box(draw, (795, 460, 1085, 600), "TopicWeightage", "topic, required_marks, offered_marks, candidate notes.", "#f1f5f9")
    box(draw, (555, 700, 845, 820), "ComparisonReport", "job_id plus all schemas above. Used by frontend report tables.", "#dcfce7")

    arrow(draw, (215, 270), (600, 700), "baseline")
    arrow(draw, (700, 270), (685, 700), "paper")
    arrow(draw, (1185, 270), (760, 700), "AI/map")
    arrow(draw, (460, 600), (625, 700), "rules")
    arrow(draw, (940, 600), (755, 700), "charts")

    img.save(OUT / "data_contracts.png")


if __name__ == "__main__":
    system_architecture()
    frontend_flow()
    backend_pipeline()
    local_model_testing()
    data_contracts()
    print(f"Wrote diagrams to {OUT}")
