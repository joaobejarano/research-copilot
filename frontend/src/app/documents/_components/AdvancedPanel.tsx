import type { SyntheticEvent } from "react";
import type { DocumentChunkModel, DocumentStatusModel } from "../../../lib/api/models/documents";

interface AdvancedPanelProps {
  detail: DocumentStatusModel;
  isProcessing: boolean;
  isDetailLoading: boolean;
  documentChunks: DocumentChunkModel[];
  chunksCountFromApi: number | null;
  isChunksLoading: boolean;
  chunksErrorMessage: string | null;
  isAdvancedOpen: boolean;
  onToggle: (event: SyntheticEvent<HTMLDetailsElement>) => void;
  onRefreshChunks: () => void;
}

export function AdvancedPanel({
  detail,
  isProcessing,
  isDetailLoading,
  documentChunks,
  chunksCountFromApi,
  isChunksLoading,
  chunksErrorMessage,
  isAdvancedOpen,
  onToggle,
  onRefreshChunks,
}: AdvancedPanelProps) {
  return (
    <details className="advanced-panel" open={isAdvancedOpen} onToggle={onToggle}>
      <summary className="advanced-summary">6. Inspect evidence (advanced)</summary>

      <div className="advanced-content">
        <div className="advanced-meta-grid">
          <article className="advanced-meta-card">
            <p className="summary-label">storage path</p>
            <p className="advanced-meta-value">{detail.storage_path}</p>
          </article>
          <article className="advanced-meta-card">
            <p className="summary-label">document status</p>
            <p className="advanced-meta-value">{detail.status}</p>
          </article>
          <article className="advanced-meta-card">
            <p className="summary-label">chunks count</p>
            <p className="advanced-meta-value">
              {chunksCountFromApi === null ? "not loaded" : chunksCountFromApi}
            </p>
          </article>
        </div>

        <div className="chunks-section-header">
          <h4>Chunks</h4>
          <button
            type="button"
            className="button"
            onClick={onRefreshChunks}
            disabled={isChunksLoading || isProcessing || isDetailLoading}
          >
            {isChunksLoading ? "Refreshing chunks..." : "Refresh chunks"}
          </button>
        </div>

        {isChunksLoading ? <p className="inline-loading">Loading chunks...</p> : null}

        {!isChunksLoading && chunksErrorMessage ? (
          <section className="error-panel">
            <p>Could not load chunks: {chunksErrorMessage}</p>
            <button
              type="button"
              className="button"
              onClick={onRefreshChunks}
              disabled={isProcessing || isDetailLoading}
            >
              Retry chunks
            </button>
          </section>
        ) : null}

        {!isChunksLoading && !chunksErrorMessage && documentChunks.length === 0 ? (
          <p className="empty-hint">No chunks available for this document.</p>
        ) : null}

        {!isChunksLoading && !chunksErrorMessage && documentChunks.length > 0 ? (
          <div className="chunks-list">
            {documentChunks.map((chunk) => (
              <article key={chunk.chunk_index} className="chunk-card">
                <header className="chunk-meta">
                  <span>chunk: {chunk.chunk_index}</span>
                  <span>page: {chunk.page_number === null ? "n/a" : chunk.page_number}</span>
                  <span>tokens: {chunk.token_count}</span>
                </header>
                <div className="chunk-text">{chunk.text}</div>
              </article>
            ))}
          </div>
        ) : null}
      </div>
    </details>
  );
}
