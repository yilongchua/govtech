type Report = {
  job_id: string;
  exam_paper: {
    subject: string;
    paper_code: string;
    paper_title: string;
    total_marks: number;
    questions: Array<{ question_id: string; section: string; marks?: number | null; choice_group?: string | null }>;
    sources: Array<{ source_id: string }>;
  };
  syllabus: {
    year: number;
    subject: string;
    subject_code: string;
  };
  rule_checks: Array<{ rule_id: string; expected: string; observed: string; passed: boolean }>;
  annotations: Array<{ question_id: string; predicted_objectives: string[]; predicted_topic: string; evidence_page_numbers?: number[] }>;
  topic_weightage: Array<{ topic: string; required_marks: number; offered_marks: number }>;
  structure_metrics?: Array<{ label: string; value: string | number | null }>;
  download_filename_base?: string;
  issues: Array<{ severity: string; code: string; message: string; reason?: string }>;
};

export function ComparisonReport({ report }: { report: Report }) {
  const jsonUrl = `/api/jobs/${report.job_id}/report`;
  const docxUrl = `/api/jobs/${report.job_id}/report.docx`;
  const filenameBase = report.download_filename_base || `exam-alignment-${report.job_id}`;
  const structureMetrics = report.structure_metrics?.length
    ? report.structure_metrics
    : [
        { label: "Subject", value: report.exam_paper.subject || "Unknown" },
        { label: "Total marks", value: report.exam_paper.total_marks ?? "Unknown" },
        { label: "Question count", value: report.exam_paper.questions?.length ?? 0 },
        { label: "Source count", value: report.exam_paper.sources?.length ?? 0 },
      ];
  const checksRequiringAttention = report.rule_checks.filter((item) => !item.passed);
  const maxTopicMarks = Math.max(
    1,
    ...report.topic_weightage.map((item) => Math.max(item.required_marks, item.offered_marks)),
  );

  return (
    <section className="report">
      <div className="report-actions">
        <a href={jsonUrl} download={`${filenameBase}.json`}>Download JSON</a>
        <a href={docxUrl} download={`${filenameBase}.docx`}>Download Word report</a>
      </div>
      <div className="summary-grid">
        <div>
          <span className="label">Paper</span>
          <strong>{report.exam_paper.paper_code || "Unknown"}</strong>
          <p>{report.exam_paper.paper_title}</p>
        </div>
        <div>
          <span className="label">Syllabus</span>
          <strong>{report.syllabus.subject} {report.syllabus.subject_code}</strong>
          <p>{report.syllabus.year}</p>
        </div>
        <div>
          <span className="label">Marks</span>
          <strong>{report.exam_paper.total_marks}</strong>
          <p>candidate paper total</p>
        </div>
      </div>

      <h2>Extracted Paper Structure</h2>
      <table>
        <thead>
          <tr><th>Field</th><th>Extracted value</th></tr>
        </thead>
        <tbody>
          {structureMetrics.map((item) => (
            <tr key={item.label}><td>{item.label}</td><td>{item.value ?? "Unknown"}</td></tr>
          ))}
        </tbody>
      </table>

      <h2>Checks Requiring Attention</h2>
      {checksRequiringAttention.length === 0 ? <p>No structural checks require review.</p> : (
        <table>
          <thead>
            <tr><th>Rule</th><th>Expected</th><th>Observed</th><th>Status</th></tr>
          </thead>
          <tbody>
            {checksRequiringAttention.map((item) => (
              <tr key={item.rule_id}>
                <td>{item.rule_id}</td>
                <td>{item.expected}</td>
                <td>{item.observed}</td>
                <td><span className="fail">Review</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2>Topic Weightage</h2>
      <table>
        <thead>
          <tr><th>Topic</th><th>Required marks</th><th>Offered marks</th><th>Required vs offered</th></tr>
        </thead>
        <tbody>
          {report.topic_weightage.map((item) => {
            const offeredWidth = Math.max(item.required_marks, item.offered_marks) / maxTopicMarks * 100;
            const requiredShare = item.offered_marks > 0
              ? Math.min(100, item.required_marks / item.offered_marks * 100)
              : item.required_marks > 0 ? 100 : 0;
            return (
              <tr key={item.topic}>
                <td>{item.topic}</td>
                <td>{item.required_marks}</td>
                <td>{item.offered_marks}</td>
                <td>
                  <div
                    className="weightage-overlay"
                    aria-label={`${item.required_marks} required marks against ${item.offered_marks} offered marks`}
                    title={`${item.required_marks} required / ${item.offered_marks} offered`}
                  >
                    <div className="weightage-track" style={{ width: `${offeredWidth}%` }}>
                      <div className="weightage-required" style={{ width: `${requiredShare}%` }} />
                    </div>
                    <span>{item.required_marks}/{item.offered_marks}</span>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <h2>Objective Alignment</h2>
      <table>
        <thead>
          <tr><th>Question</th><th>Objectives</th><th>Topic</th><th>Evidence pages</th></tr>
        </thead>
        <tbody>
          {report.annotations.map((item) => (
            <tr key={item.question_id}>
              <td>{item.question_id}</td>
              <td>{item.predicted_objectives.join(", ")}</td>
              <td>{item.predicted_topic}</td>
              <td>{item.evidence_page_numbers?.join(", ") || "Not recorded"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Warnings And Errors</h2>
      {report.issues.length === 0 ? <p>No issues recorded.</p> : (
        <ul className="issue-list">
          {report.issues.map((issue, index) => (
            <li key={`${issue.code}-${index}`}>
              <strong>{issue.severity}</strong> {issue.code}: {issue.message}
              {issue.reason ? <span> {issue.reason}</span> : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
