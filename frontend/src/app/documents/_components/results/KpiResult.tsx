import type { ExtractKpisResponseModel } from "../../../../lib/api/models/documents";
import { CitationCards } from "../CitationCard";

interface KpiResultProps {
  result: ExtractKpisResponseModel;
}

export function KpiResult({ result }: KpiResultProps) {
  return (
    <>
      <div className="result-block">
        <p className="result-label">KPIs</p>
        {result.status === "insufficient_evidence" ? (
          <p className="empty-hint">Insufficient evidence. No KPIs were extracted.</p>
        ) : result.kpis.length === 0 ? (
          <p className="empty-hint">No KPIs returned.</p>
        ) : (
          <div className="structured-list">
            {result.kpis.map((kpi, index) => (
              <article key={`${kpi.name}-${index}`} className="structured-item-card">
                <p className="structured-item-title">{kpi.name}</p>
                <p className="structured-item-line">value: {kpi.value}</p>
                <p className="structured-item-line">unit: {kpi.unit ?? "n/a"}</p>
                <p className="structured-item-line">period: {kpi.period ?? "n/a"}</p>
                <p className="structured-item-line">citation: {kpi.citation}</p>
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
