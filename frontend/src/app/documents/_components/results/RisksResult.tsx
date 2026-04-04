import type { ExtractRisksResponseModel } from "../../../../lib/api/models/documents";
import { CitationCards } from "../CitationCard";

interface RisksResultProps {
  result: ExtractRisksResponseModel;
}

export function RisksResult({ result }: RisksResultProps) {
  return (
    <>
      <div className="result-block">
        <p className="result-label">Risks</p>
        {result.status === "insufficient_evidence" ? (
          <p className="empty-hint">Insufficient evidence. No risks were extracted.</p>
        ) : result.risks.length === 0 ? (
          <p className="empty-hint">No risks returned.</p>
        ) : (
          <div className="structured-list">
            {result.risks.map((risk, index) => (
              <article key={`${risk.title}-${index}`} className="structured-item-card">
                <p className="structured-item-title">{risk.title}</p>
                <p className="structured-item-line">severity: {risk.severity_or_materiality}</p>
                <p className="structured-item-line">citation: {risk.citation}</p>
                <p className="result-text">{risk.description}</p>
              </article>
            ))}
          </div>
        )}
      </div>

      <div className="result-block">
        <p className="result-label">Evidence citations</p>
        <CitationCards citations={result.evidence.citations} />
      </div>
    </>
  );
}
