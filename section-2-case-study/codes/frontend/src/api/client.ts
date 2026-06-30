const API_BASE = "";

export type ModelProvider = "lm-studio" | "openai-compatible" | "ollama" | "mock";

export type ModelSettings = {
  provider: ModelProvider;
  base_url: string;
  model: string;
  timeout_seconds: number;
};

export type SyllabusIngestionResult = {
  ok: boolean;
  subject: string;
  subject_code: string;
  year: number;
  pdf_url: string;
  pdf_path: string;
  markdown_path: string;
  json_path: string;
  extraction_artifact_path: string;
  source_page_url: string;
  issues: Array<{ severity: string; message: string }>;
};

export type SyllabusIngestionEvent = {
  status: "running" | "complete" | "failed";
  stage: string;
  progress: number;
  step: number;
  total_steps: number;
  message: string;
  detail?: string;
  error?: string;
  llm_call?: {
    provider: string;
    base_url: string;
    model: string;
    timeout_seconds: number;
    goal: string;
  };
  result?: SyllabusIngestionResult;
};

export type SyllabusSummary = {
  subject: string;
  subject_code: string;
  year: number;
  source_page_url: string;
  pdf_url: string;
  pdf_url_local: string;
  json_path: string;
  markdown_path: string;
  configured: boolean;
};

export type SyllabusRequirement = {
  type: string;
  reference: string;
  requirement: string;
  details: string;
  page: number | null;
  marks?: number | null;
};

export type SyllabusDetail = {
  entry: SyllabusSummary;
  syllabus: {
    issues?: Array<{ severity: string; message: string }>;
    objectives?: unknown[];
    components?: unknown[];
    topics?: unknown[];
  };
  requirements: SyllabusRequirement[];
};

export async function getLatestSyllabus() {
  const response = await fetch(`${API_BASE}/api/syllabus/latest`);
  if (!response.ok) throw new Error("Failed to load syllabus metadata");
  return response.json();
}

export async function uploadPaper(file: File) {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_BASE}/api/uploads`, {
    method: "POST",
    body: form
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function uploadPapers(files: File[], syllabusSubjectCode?: string) {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  if (syllabusSubjectCode) form.append("syllabus_subject_code", syllabusSubjectCode);
  const response = await fetch(`${API_BASE}/api/uploads/batch`, {
    method: "POST",
    body: form
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function listSyllabuses(): Promise<SyllabusSummary[]> {
  const response = await fetch(`${API_BASE}/api/syllabuses`);
  if (!response.ok) throw new Error("Failed to load syllabuses");
  const payload = await response.json();
  return payload.syllabuses ?? [];
}

export async function getSyllabusDetail(subjectCode: string): Promise<SyllabusDetail> {
  const response = await fetch(`${API_BASE}/api/syllabuses/${encodeURIComponent(subjectCode)}`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function deleteSyllabus(subjectCode: string) {
  const response = await fetch(`${API_BASE}/api/syllabuses/${encodeURIComponent(subjectCode)}`, {
    method: "DELETE"
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function ingestSyllabusUrl(url: string, label?: string): Promise<SyllabusIngestionResult> {
  const response = await fetch(`${API_BASE}/api/syllabuses/ingest-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, label: label || undefined })
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function ingestSyllabusUrlWithEvents(
  url: string,
  label: string | undefined,
  onEvent: (event: SyllabusIngestionEvent) => void
): Promise<SyllabusIngestionResult> {
  const response = await fetch(`${API_BASE}/api/syllabuses/ingest-url/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, label: label || undefined })
  });
  if (!response.ok) throw new Error(await response.text());
  if (!response.body) throw new Error("Syllabus ingestion stream was not available");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult: SyllabusIngestionResult | null = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";
    for (const rawEvent of events) {
      const dataLine = rawEvent.split("\n").find((line) => line.startsWith("data: "));
      if (!dataLine) continue;
      const event = JSON.parse(dataLine.slice(6)) as SyllabusIngestionEvent;
      onEvent(event);
      if (event.status === "failed") throw new Error(event.error || event.message);
      if (event.status === "complete" && event.result) finalResult = event.result;
    }
  }

  if (!finalResult) throw new Error("Syllabus ingestion ended before a completion event was received");
  return finalResult;
}

export async function getModelSettings(): Promise<ModelSettings> {
  const response = await fetch(`${API_BASE}/api/model-settings`);
  if (!response.ok) throw new Error("Failed to load model settings");
  return response.json();
}

export async function saveModelSettings(settings: ModelSettings): Promise<ModelSettings> {
  const response = await fetch(`${API_BASE}/api/model-settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings)
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function getModels(settings: ModelSettings): Promise<string[]> {
  const response = await fetch(`${API_BASE}/api/model-settings/models`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings)
  });
  if (!response.ok) throw new Error(await response.text());
  const payload = await response.json();
  return payload.models ?? [];
}

export async function testModelConnection(settings: ModelSettings) {
  const response = await fetch(`${API_BASE}/api/model-settings/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings)
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export function reportJsonUrl(jobId: string) {
  return `${API_BASE}/api/jobs/${jobId}/report`;
}

export function reportDocxUrl(jobId: string) {
  return `${API_BASE}/api/jobs/${jobId}/report.docx`;
}

export function batchReportsZipUrl(batchId: string) {
  return `${API_BASE}/api/batches/${batchId}/reports.zip`;
}
