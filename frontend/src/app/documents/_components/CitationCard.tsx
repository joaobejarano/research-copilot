import type { GroundedCitationModel } from "../../../lib/api/models/documents";

interface CitationCardProps {
  citation: GroundedCitationModel;
}

export function CitationCard({ citation }: CitationCardProps) {
  return (
    <article className="citation-card">
      <header className="citation-meta">
        <span>{citation.citation_id}</span>
        <span>rank: {citation.rank}</span>
        <span>chunk: {citation.chunk_index}</span>
        <span>page: {citation.page_number === null ? "n/a" : citation.page_number}</span>
        <span>score: {citation.retrieval_score.toFixed(3)}</span>
      </header>
      <div className="citation-text">{citation.text_excerpt}</div>
    </article>
  );
}

interface CitationCardsProps {
  citations: GroundedCitationModel[];
}

export function CitationCards({ citations }: CitationCardsProps) {
  if (citations.length === 0) {
    return <p className="empty-hint">No citations returned.</p>;
  }

  return (
    <div className="citations-list">
      {[...citations]
        .sort((a, b) => a.rank - b.rank)
        .map((citation) => (
          <CitationCard key={citation.citation_id} citation={citation} />
        ))}
    </div>
  );
}
