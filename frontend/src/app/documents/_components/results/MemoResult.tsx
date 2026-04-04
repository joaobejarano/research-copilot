import type { GenerateMemoResponseModel } from "../../../../lib/api/models/documents";

interface MemoResultProps {
  result: GenerateMemoResponseModel;
}

export function MemoResult({ result }: MemoResultProps) {
  if (result.status === "insufficient_evidence" || result.memo === null) {
    return <p className="empty-hint">Insufficient evidence. No memo content was generated.</p>;
  }

  const sectionRows = [
    { label: "Key developments", items: result.memo.key_developments },
    { label: "Risks", items: result.memo.risks },
    { label: "Catalysts", items: result.memo.catalysts },
    { label: "KPIs", items: result.memo.kpis },
    { label: "Open questions", items: result.memo.open_questions },
  ];

  const sectionCitations = [
    { label: "Company overview", ids: result.memo.citations_by_section.company_overview },
    { label: "Key developments", ids: result.memo.citations_by_section.key_developments },
    { label: "Risks", ids: result.memo.citations_by_section.risks },
    { label: "Catalysts", ids: result.memo.citations_by_section.catalysts },
    { label: "KPIs", ids: result.memo.citations_by_section.kpis },
    { label: "Open questions", ids: result.memo.citations_by_section.open_questions },
  ];

  return (
    <>
      <div className="result-block">
        <p className="result-label">Company overview</p>
        <p className="result-text">{result.memo.company_overview}</p>
      </div>

      {sectionRows.map((row) => (
        <div className="result-block" key={row.label}>
          <p className="result-label">{row.label}</p>
          {row.items.length === 0 ? (
            <p className="empty-hint">No items returned.</p>
          ) : (
            <ul className="result-list">
              {row.items.map((item, index) => (
                <li key={`${row.label}-${index}`}>{item}</li>
              ))}
            </ul>
          )}
        </div>
      ))}

      <div className="result-block">
        <p className="result-label">Section citations</p>
        <div className="citation-id-grid">
          {sectionCitations.map((entry) => (
            <article key={entry.label} className="citation-id-card">
              <p className="citation-id-title">{entry.label}</p>
              <p className="citation-id-values">
                {entry.ids.length > 0 ? entry.ids.join(", ") : "No citations"}
              </p>
            </article>
          ))}
        </div>
      </div>
    </>
  );
}
