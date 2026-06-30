import React, { useEffect, useMemo, useState } from "react";
import { BookOpen, ExternalLink, FileArchive, FileText, Link, LoaderCircle, Send, Settings, Trash2 } from "lucide-react";
import {
  batchReportsZipUrl,
  deleteSyllabus,
  getSyllabusDetail,
  ingestSyllabusUrlWithEvents,
  listSyllabuses,
  uploadPapers,
  type SyllabusIngestionEvent,
  type SyllabusDetail,
  type SyllabusIngestionResult,
  type SyllabusSummary
} from "./api/client";
import { UploadDropzone } from "./components/UploadDropzone";
import { ProgressBar } from "./components/ProgressBar";
import { ComparisonReport } from "./components/ComparisonReport";
import { ErrorPanel } from "./components/ErrorPanel";
import { ModelSettingsPanel } from "./components/ModelSettingsPanel";
import "./styles/main.css";

type AppTab = "papers" | "syllabuses";

const exampleSeabUrl =
  "https://www.seab.gov.sg/gce-o-level/o-level-syllabuses-examined-for-school-candidates-2026/#:~:text=Bahasa%20Indonesia%20as%20a%203rd%20Language";

export default function App() {
  const [activeTab, setActiveTab] = useState<AppTab>("papers");
  const [files, setFiles] = useState<File[]>([]);
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState("Ready");
  const [batchId, setBatchId] = useState<string | null>(null);
  const [reports, setReports] = useState<Array<{ jobId: string; filename: string; report: any }>>([]);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [syllabuses, setSyllabuses] = useState<SyllabusSummary[]>([]);
  const [selectedSyllabusCode, setSelectedSyllabusCode] = useState("");
  const [selectedSyllabusDetail, setSelectedSyllabusDetail] = useState<SyllabusDetail | null>(null);
  const [syllabusListError, setSyllabusListError] = useState<string | null>(null);
  const [isLoadingSyllabuses, setIsLoadingSyllabuses] = useState(false);
  const [syllabusUrl, setSyllabusUrl] = useState(exampleSeabUrl);
  const [syllabusStatus, setSyllabusStatus] = useState("Ready");
  const [syllabusError, setSyllabusError] = useState<string | null>(null);
  const [syllabusResult, setSyllabusResult] = useState<SyllabusIngestionResult | null>(null);
  const [syllabusEvents, setSyllabusEvents] = useState<SyllabusIngestionEvent[]>([]);
  const [isIngestingSyllabus, setIsIngestingSyllabus] = useState(false);
  const [isDeletingSyllabus, setIsDeletingSyllabus] = useState(false);
  const activeReport = reports.find((item) => item.jobId === activeJobId) ?? reports[0];
  const selectedSyllabus = useMemo(
    () => syllabuses.find((item) => item.subject_code === selectedSyllabusCode) ?? null,
    [selectedSyllabusCode, syllabuses]
  );
  const currentSyllabusEvent = syllabusEvents[syllabusEvents.length - 1] ?? null;

  const loadSyllabuses = async (preferredCode?: string) => {
    setIsLoadingSyllabuses(true);
    setSyllabusListError(null);
    try {
      const nextSyllabuses = await listSyllabuses();
      setSyllabuses(nextSyllabuses);
      const preferred = preferredCode ?? selectedSyllabusCode;
      const preferredExists = nextSyllabuses.some((item) => item.subject_code === preferred);
      const nextCode = preferredExists ? preferred : nextSyllabuses.find((item) => item.configured)?.subject_code || nextSyllabuses[0]?.subject_code || "";
      setSelectedSyllabusCode(nextCode);
    } catch (err) {
      setSyllabusListError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoadingSyllabuses(false);
    }
  };

  useEffect(() => {
    loadSyllabuses();
  }, []);

  useEffect(() => {
    if (!selectedSyllabusCode) {
      setSelectedSyllabusDetail(null);
      return;
    }
    let cancelled = false;
    getSyllabusDetail(selectedSyllabusCode)
      .then((detail) => {
        if (!cancelled) setSelectedSyllabusDetail(detail);
      })
      .catch((err) => {
        if (!cancelled) {
          setSelectedSyllabusDetail(null);
          setSyllabusListError(err instanceof Error ? err.message : String(err));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedSyllabusCode]);

  const submit = async () => {
    if (files.length === 0) return;
    setError(null);
    setReports([]);
    setActiveJobId(null);
    setBatchId(null);
    setProgress(15);
    setStage(files.length === 1 ? "Uploading" : `Uploading ${files.length} PDFs`);
    try {
      setProgress(35);
      setStage(files.length === 1 ? "Analysing exam paper" : "Analysing exam papers");
      const result = await uploadPapers(files, selectedSyllabusCode);
      const completedReports = (result.jobs ?? [])
        .filter((job: any) => job.status === "complete" && job.report)
        .map((job: any) => ({ jobId: job.job_id, filename: job.filename, report: job.report }));
      const failedJobs = (result.jobs ?? []).filter((job: any) => job.status === "failed");
      setProgress(100);
      setStage(result.status === "partial" ? "Complete with errors" : "Complete");
      setBatchId(result.batch_id);
      setReports(completedReports);
      setActiveJobId(completedReports[0]?.jobId ?? null);
      if (failedJobs.length > 0) {
        setError(`${failedJobs.length} file${failedJobs.length === 1 ? "" : "s"} failed. ${failedJobs.map((job: any) => job.filename).join(", ")}`);
      }
      if (completedReports.length === 0) {
        throw new Error(failedJobs[0]?.error || "No reports were generated.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStage("Failed");
      setProgress(100);
    }
  };

  const ingestSyllabus = async () => {
    if (!syllabusUrl.trim()) return;
    setSyllabusError(null);
    setSyllabusResult(null);
    setSyllabusEvents([]);
    setIsIngestingSyllabus(true);
    setSyllabusStatus("Resolving SEAB syllabus link");
    try {
      const result = await ingestSyllabusUrlWithEvents(syllabusUrl.trim(), undefined, (event) => {
        setSyllabusEvents((current) => [...current, event]);
        setSyllabusStatus(event.message);
      });
      setSyllabusResult(result);
      setSyllabusStatus("Ingested");
      await loadSyllabuses(result.subject_code);
    } catch (err) {
      setSyllabusError(err instanceof Error ? err.message : String(err));
      setSyllabusStatus("Failed");
    } finally {
      setIsIngestingSyllabus(false);
    }
  };

  const removeSelectedSyllabus = async () => {
    if (!selectedSyllabus) return;
    const confirmed = window.confirm(`Remove ${selectedSyllabus.subject} (${selectedSyllabus.subject_code}) from syllabuses?`);
    if (!confirmed) return;
    setIsDeletingSyllabus(true);
    setSyllabusListError(null);
    try {
      await deleteSyllabus(selectedSyllabus.subject_code);
      setSelectedSyllabusDetail(null);
      setSyllabusResult(null);
      await loadSyllabuses("");
    } catch (err) {
      setSyllabusListError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsDeletingSyllabus(false);
    }
  };

  return (
    <main className="shell">
      <nav className="app-nav" aria-label="Primary">
        <div className="brand-lockup">
          <FileText size={24} />
          <span>Exam Paper Alignment</span>
        </div>
        <div className="nav-tabs" role="tablist" aria-label="Application sections">
          <button type="button" className={activeTab === "papers" ? "active" : ""} onClick={() => setActiveTab("papers")}>
            <FileText size={17} />
            Papers
          </button>
          <button type="button" className={activeTab === "syllabuses" ? "active" : ""} onClick={() => setActiveTab("syllabuses")}>
            <BookOpen size={17} />
            Syllabuses
          </button>
        </div>
        <button
          className="nav-icon-button"
          type="button"
          onClick={() => setIsSettingsOpen(true)}
          title="LLM settings"
          aria-label="LLM settings"
        >
          <Settings size={20} />
        </button>
      </nav>

      <header className="topbar">
        <div>
          <h1>{activeTab === "papers" ? "Exam Paper Alignment" : "Syllabuses"}</h1>
          <p>
            {activeTab === "papers"
              ? "Upload one or more exam paper PDFs. The backend scans each first page, selects the best subject route, and compares the paper against the configured syllabus baseline."
              : "Add a SEAB syllabus page text-fragment URL or a direct syllabus PDF URL. The POC resolves the selected SEAB link, downloads the PDF, and stores it as an ingested syllabus."}
          </p>
        </div>
      </header>

      {activeTab === "papers" ? (
        <section className="workspace">
          <div className="paper-source-row">
            <label className="field">
              <span>Compare against syllabus</span>
              <select value={selectedSyllabusCode} onChange={(event) => setSelectedSyllabusCode(event.target.value)}>
                {syllabuses.map((item) => (
                  <option key={item.subject_code} value={item.subject_code}>
                    {item.subject} ({item.subject_code}, {item.year}){item.configured ? "" : " - extraction pending"}
                  </option>
                ))}
              </select>
            </label>
            {selectedSyllabus ? (
              <div className={`source-health ${selectedSyllabus.configured ? "ready" : "pending"}`}>
                {selectedSyllabus.configured ? "Comparison-ready" : "Requirements extraction pending"}
              </div>
            ) : null}
          </div>
          <UploadDropzone
            files={files}
            onFiles={(nextFiles) => {
              setError(null);
              setFiles(nextFiles);
              setReports([]);
              setActiveJobId(null);
              setBatchId(null);
            }}
            onInvalidFile={setError}
          />
          <div className="actions">
            <button className="submit" disabled={files.length === 0} onClick={submit}>
              <Send size={18} />
              Submit
            </button>
          </div>
          {progress > 0 ? <ProgressBar progress={progress} stage={stage} /> : null}
          {error ? <ErrorPanel message={error} /> : null}
        </section>
      ) : (
        <section className="workspace syllabus-workspace">
          <div className="syllabus-top-grid">
            <div className="syllabus-ingest-panel">
              <div className="panel-heading">
                <Link size={18} />
                <h2>Add Syllabus</h2>
              </div>
              <div className="url-fields">
                <label className="field">
                  <span>SEAB URL or PDF link</span>
                  <input value={syllabusUrl} onChange={(event) => setSyllabusUrl(event.target.value)} placeholder={exampleSeabUrl} />
                </label>
              </div>
              <div className="actions compact-actions">
                <button className="submit" disabled={!syllabusUrl.trim() || isIngestingSyllabus} onClick={ingestSyllabus}>
                  {isIngestingSyllabus ? <LoaderCircle className="spin" size={18} /> : <Link size={18} />}
                  Ingest Syllabus
                </button>
              </div>
              <div className={`settings-status status-with-step ${syllabusStatus === "Ingested" ? "success" : ""}`}>
                <span>{syllabusStatus}</span>
                {currentSyllabusEvent ? (
                  <strong>{currentSyllabusEvent.step}/{currentSyllabusEvent.total_steps} steps</strong>
                ) : null}
              </div>
              {syllabusEvents.length ? (
                <div className="ingestion-timeline" aria-live="polite">
                  {syllabusEvents.map((event, index) => (
                    <div className={`timeline-row ${event.status}`} key={`${event.stage}-${index}`}>
                      <div className="timeline-progress">
                        {event.step}/{event.total_steps}
                      </div>
                      <div>
                        <strong>{event.message}</strong>
                        {event.detail ? <p>{event.detail}</p> : null}
                        {event.llm_call ? (
                          <div className="llm-call">
                            <span>{event.llm_call.provider}</span>
                            <span>{event.llm_call.model}</span>
                            <span>{event.llm_call.timeout_seconds}s</span>
                            <p>{event.llm_call.goal}</p>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
              {syllabusError ? <ErrorPanel message={syllabusError} /> : null}
              {syllabusResult ? (
                <div className="ingestion-result">
                  <div>
                    <span className="label">Syllabus</span>
                    <strong>{syllabusResult.subject}</strong>
                    <p>{syllabusResult.subject_code} - {syllabusResult.year}</p>
                  </div>
                  <div>
                    <span className="label">Stored artifacts</span>
                    <p>{syllabusResult.pdf_path}</p>
                    <p>{syllabusResult.markdown_path}</p>
                    <p>{syllabusResult.json_path}</p>
                  </div>
                  <a href={syllabusResult.pdf_url} target="_blank" rel="noreferrer">Open source PDF</a>
                </div>
              ) : null}
            </div>
            <div className="syllabus-select-panel">
              <div className="panel-heading">
                <BookOpen size={18} />
                <h2>Select Subject</h2>
              </div>
              <div className="syllabus-browser">
                <label className="field">
                  <span className="field-label-row">
                    Subject
                    {selectedSyllabusDetail ? (
                      <a className="source-icon-link" href={selectedSyllabusDetail.entry.pdf_url} target="_blank" rel="noreferrer" title="Open original source PDF" aria-label="Open original source PDF">
                        <ExternalLink size={18} />
                      </a>
                    ) : null}
                  </span>
                  <select value={selectedSyllabusCode} onChange={(event) => setSelectedSyllabusCode(event.target.value)} disabled={isLoadingSyllabuses}>
                    {syllabuses.map((item) => (
                      <option key={item.subject_code} value={item.subject_code}>
                        {item.subject} ({item.subject_code}, {item.year})
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  className="delete-icon-button"
                  type="button"
                  onClick={removeSelectedSyllabus}
                  disabled={!selectedSyllabus || isDeletingSyllabus}
                  title="Delete selected syllabus"
                  aria-label="Delete selected syllabus"
                >
                  {isDeletingSyllabus ? <LoaderCircle className="spin" size={17} /> : <Trash2 size={17} />}
                </button>
              </div>
              {syllabusListError ? <ErrorPanel message={syllabusListError} /> : null}
              {selectedSyllabusDetail ? (
                <div className="source-panel">
                  <div>
                    <strong>{selectedSyllabusDetail.entry.subject}</strong>
                    <p>{selectedSyllabusDetail.entry.subject_code} - {selectedSyllabusDetail.entry.year}</p>
                  </div>
                  <div className={`source-health ${selectedSyllabusDetail.entry.configured ? "ready" : "pending"}`}>
                    {selectedSyllabusDetail.entry.configured ? "Ready for source comparison" : "PDF ingested, structured extractor pending"}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
          {selectedSyllabusDetail ? (
            <div className="requirements-table-wrap">
              <div className="section-heading">
                <h2>Current Syllabus Requirements</h2>
                <p>{selectedSyllabusDetail.requirements.length} cited row{selectedSyllabusDetail.requirements.length === 1 ? "" : "s"}</p>
              </div>
              <table className="requirements-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Source</th>
                    <th>Requirement</th>
                    <th>Page</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedSyllabusDetail.requirements.map((row, index) => (
                    <tr key={`${row.type}-${row.reference}-${index}`}>
                      <td>{row.type}</td>
                      <td>{row.reference}</td>
                      <td>
                        {row.requirement}
                        {row.details || row.marks ? (
                          <span className="requirement-meta">{row.details || `${row.marks} marks`}</span>
                        ) : null}
                      </td>
                      <td>{row.page ? `p. ${row.page}` : "Needs citation"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
          {selectedSyllabusDetail ? (
            <div className="pdf-preview-section">
              <div className="section-heading">
                <h2>Original Syllabus PDF</h2>
                <a className="source-icon-link" href={selectedSyllabusDetail.entry.pdf_url} target="_blank" rel="noreferrer" title="Open original source PDF" aria-label="Open original source PDF">
                  <ExternalLink size={18} />
                </a>
              </div>
              <iframe className="pdf-preview" title="Original syllabus PDF" src={selectedSyllabusDetail.entry.pdf_url_local} />
            </div>
          ) : null}
        </section>
      )}

      <ModelSettingsPanel open={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />

      {activeTab === "papers" && reports.length > 0 ? (
        <section className="batch-results">
          <div className="batch-header">
            <div>
              <h2>Generated Reports</h2>
              <p>{reports.length} report{reports.length === 1 ? "" : "s"} ready</p>
            </div>
            {batchId ? (
              <a className="archive-download" href={batchReportsZipUrl(batchId)} download={`exam-alignment-reports-${batchId}.zip`}>
                <FileArchive size={18} />
                Download ZIP
              </a>
            ) : null}
          </div>
          <div className="report-tabs" role="tablist" aria-label="Uploaded documents">
            {reports.map((item, index) => (
              <button
                key={item.jobId}
                type="button"
                role="tab"
                aria-selected={item.jobId === activeReport?.jobId}
                className={item.jobId === activeReport?.jobId ? "active" : ""}
                onClick={() => setActiveJobId(item.jobId)}
              >
                {item.filename || `Document ${index + 1}`}
              </button>
            ))}
          </div>
          {activeReport ? <ComparisonReport report={activeReport.report} /> : null}
        </section>
      ) : null}
    </main>
  );
}
