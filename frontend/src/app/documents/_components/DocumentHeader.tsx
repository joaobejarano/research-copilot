import type { DocumentStatusModel } from "../../../lib/api/models/documents";
import { formatCreatedAt, getStatusTone } from "./shared";

interface DocumentHeaderProps {
  detail: DocumentStatusModel;
  isProcessing: boolean;
  isDetailLoading: boolean;
  processingStatusMessage: string | null;
  processingErrorMessage: string | null;
  onProcess: () => void;
  onRefreshDetail: () => void;
}

export function DocumentHeader({
  detail,
  isProcessing,
  isDetailLoading,
  processingStatusMessage,
  processingErrorMessage,
  onProcess,
  onRefreshDetail,
}: DocumentHeaderProps) {
  const statusTone = getStatusTone(detail.status);

  return (
    <>
      <header className="document-workspace-header">
        <div>
          <h3 className="workspace-title">
            {detail.company_name} · {detail.period}
          </h3>
          <p className="workspace-meta-line">
            #{detail.id} · {detail.document_type}
          </p>
          <p className="workspace-meta-line subtle-text">{detail.source_filename}</p>
        </div>
        <div className="workspace-status-card">
          <p className="summary-label">status</p>
          <span className={`status-pill ${statusTone}`}>{detail.status}</span>
          <p className="workspace-meta-line subtle-text" title={detail.created_at}>
            created {formatCreatedAt(detail.created_at)}
          </p>
        </div>
      </header>

      <div className="workspace-controls-row">
        <div>
          <p className="step-title">3. Process if needed</p>
          {detail.status !== "ready" ? (
            <button
              type="button"
              className="button"
              onClick={onProcess}
              disabled={isProcessing}
            >
              {isProcessing ? "Processing..." : "Process document"}
            </button>
          ) : (
            <p className="ready-text">Document is ready for research actions.</p>
          )}
        </div>

        <button
          type="button"
          className="button"
          onClick={onRefreshDetail}
          disabled={isProcessing || isDetailLoading}
        >
          Refresh status
        </button>
      </div>

      {processingStatusMessage ? (
        <p className="status-transition">{processingStatusMessage}</p>
      ) : null}

      {processingErrorMessage ? (
        <section className="error-panel">
          <p>Document processing failed: {processingErrorMessage}</p>
        </section>
      ) : null}

      {detail.status === "failed" ? (
        <section className="error-panel">
          <p>
            This document is in <strong>failed</strong> status. Reprocess before using research
            actions.
          </p>
        </section>
      ) : null}

      {detail.status === "processing" ? (
        <section className="state-panel compact">
          <p className="state-title">Document is still processing</p>
          <p>Wait for ready status before running research actions.</p>
        </section>
      ) : null}
    </>
  );
}
