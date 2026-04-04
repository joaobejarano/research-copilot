import type { BuildTimelineResponseModel } from "../../../../lib/api/models/documents";
import { CitationCards } from "../CitationCard";

interface TimelineResultProps {
  result: BuildTimelineResponseModel;
}

export function TimelineResult({ result }: TimelineResultProps) {
  return (
    <>
      <div className="result-block">
        <p className="result-label">Timeline events</p>
        {result.status === "insufficient_evidence" ? (
          <p className="empty-hint">Insufficient evidence. No timeline events were built.</p>
        ) : result.events.length === 0 ? (
          <p className="empty-hint">No events returned.</p>
        ) : (
          <div className="structured-list">
            {result.events.map((event, index) => (
              <article key={`${event.event_date_or_period}-${index}`} className="structured-item-card">
                <p className="structured-item-title">{event.event_date_or_period}</p>
                <p className="structured-item-line">citation: {event.citation}</p>
                <p className="result-text">{event.event_summary}</p>
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
