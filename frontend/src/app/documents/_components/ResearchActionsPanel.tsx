import type { FormEvent } from "react";
import { getResultTitle, type ResearchActionType } from "./shared";

interface ResearchActionsPanelProps {
  canRunActions: boolean;
  isActionLoading: boolean;
  isDetailLoading: boolean;
  isProcessing: boolean;
  isDocumentReady: boolean;
  activeAction: ResearchActionType;
  questionInput: string;
  onActionChange: (action: ResearchActionType) => void;
  onQuestionChange: (value: string) => void;
  onAskSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onRunAction: () => void;
}

const ACTION_BUTTONS: Array<{ action: ResearchActionType; label: string }> = [
  { action: "ask", label: "Ask" },
  { action: "memo", label: "Generate memo" },
  { action: "extract_kpis", label: "Extract KPIs" },
  { action: "extract_risks", label: "Extract risks" },
  { action: "timeline", label: "Build timeline" },
];

export function ResearchActionsPanel({
  canRunActions,
  isActionLoading,
  isDetailLoading,
  isProcessing,
  isDocumentReady,
  activeAction,
  questionInput,
  onActionChange,
  onQuestionChange,
  onAskSubmit,
  onRunAction,
}: ResearchActionsPanelProps) {
  return (
    <section className="research-actions-panel">
      <p className="step-title">4. Choose a research action</p>
      <div className="research-action-tabs" role="tablist" aria-label="Research actions">
        {ACTION_BUTTONS.map(({ action, label }) => (
          <button
            key={action}
            type="button"
            className={activeAction === action ? "button action-tab active" : "button action-tab"}
            onClick={() => onActionChange(action)}
            disabled={isActionLoading || isDetailLoading || isProcessing}
          >
            {label}
          </button>
        ))}
      </div>

      {activeAction === "ask" ? (
        <form className="qa-form" onSubmit={onAskSubmit}>
          <label htmlFor="grounded-question-input" className="qa-label">
            Ask a question about this document
          </label>
          <textarea
            id="grounded-question-input"
            className="qa-input"
            value={questionInput}
            onChange={(event) => onQuestionChange(event.target.value)}
            placeholder="Example: What changed in revenue this quarter?"
            rows={3}
            disabled={!canRunActions}
          />
          <div className="qa-actions">
            <button
              type="submit"
              className="button"
              disabled={!canRunActions || questionInput.trim().length === 0}
            >
              {isActionLoading ? "Running Ask..." : "Run Ask"}
            </button>
          </div>
        </form>
      ) : (
        <div className="single-action-panel">
          <p className="section-note action-note">
            Run <strong>{getResultTitle(activeAction)}</strong> on the selected document.
          </p>
          <button
            type="button"
            className="button"
            onClick={onRunAction}
            disabled={!canRunActions}
          >
            {isActionLoading
              ? `Running ${getResultTitle(activeAction)}...`
              : `Run ${getResultTitle(activeAction)}`}
          </button>
        </div>
      )}

      {!isDocumentReady ? (
        <p className="empty-hint">Research actions unlock when document status is ready.</p>
      ) : null}
    </section>
  );
}
