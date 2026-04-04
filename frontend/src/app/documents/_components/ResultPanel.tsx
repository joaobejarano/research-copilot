import { getResultStatus, getResultTitle, type ResearchActionResult, type ResearchActionType } from "./shared";
import { AskResult } from "./results/AskResult";
import { KpiResult } from "./results/KpiResult";
import { MemoResult } from "./results/MemoResult";
import { RisksResult } from "./results/RisksResult";
import { TimelineResult } from "./results/TimelineResult";

interface ResultPanelProps {
  isActionLoading: boolean;
  activeAction: ResearchActionType;
  actionErrorMessage: string | null;
  actionResult: ResearchActionResult | null;
  streamingStatusMessage: string | null;
}

function ResultContent({ result }: { result: ResearchActionResult }) {
  if (result.action === "ask") return <AskResult result={result.response} />;
  if (result.action === "memo") return <MemoResult result={result.response} />;
  if (result.action === "extract_kpis") return <KpiResult result={result.response} />;
  if (result.action === "extract_risks") return <RisksResult result={result.response} />;
  return <TimelineResult result={result.response} />;
}

export function ResultPanel({ isActionLoading, activeAction, actionErrorMessage, actionResult, streamingStatusMessage }: ResultPanelProps) {
  const status = actionResult ? getResultStatus(actionResult) : null;

  return (
    <section className="result-panel">
      <p className="step-title">5. View result</p>

      {isActionLoading ? (
        <p className="inline-loading">
          {streamingStatusMessage ?? `Running ${getResultTitle(activeAction)}...`}
        </p>
      ) : null}

      {actionErrorMessage ? (
        <section className="error-panel">
          <p>Action failed: {actionErrorMessage}</p>
        </section>
      ) : null}

      {actionResult ? (
        <article className="action-result-card">
          <div className="qa-status-row">
            <span className="qa-status-label">action:</span>
            <span className="qa-status-badge">{getResultTitle(actionResult.action)}</span>
            <span className="qa-status-label">status:</span>
            <span
              className={
                status === "insufficient_evidence"
                  ? "qa-status-badge insufficient"
                  : "qa-status-badge answered"
              }
            >
              {status}
            </span>
          </div>
          <ResultContent result={actionResult} />
        </article>
      ) : !isActionLoading && !actionErrorMessage ? (
        <p className="empty-hint">Run one of the research actions to view output here.</p>
      ) : null}
    </section>
  );
}
