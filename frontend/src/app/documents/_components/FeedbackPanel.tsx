import type { FormEvent } from "react";
import type { FeedbackRecordModel, FeedbackValue } from "../../../lib/api/models/feedback";
import { formatCreatedAt, type ResearchActionResult } from "./shared";

interface FeedbackPanelProps {
  actionResult: ResearchActionResult | null;
  feedbackValue: FeedbackValue;
  feedbackReason: string;
  feedbackReviewerNote: string;
  isSubmittingFeedback: boolean;
  feedbackSubmitErrorMessage: string | null;
  feedbackSubmitStatusMessage: string | null;
  feedbackRecords: FeedbackRecordModel[];
  isFeedbackLoading: boolean;
  feedbackLoadErrorMessage: string | null;
  onValueChange: (value: FeedbackValue) => void;
  onReasonChange: (value: string) => void;
  onReviewerNoteChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onRefreshFeedback: () => void;
}

export function FeedbackPanel({
  actionResult,
  feedbackValue,
  feedbackReason,
  feedbackReviewerNote,
  isSubmittingFeedback,
  feedbackSubmitErrorMessage,
  feedbackSubmitStatusMessage,
  feedbackRecords,
  isFeedbackLoading,
  feedbackLoadErrorMessage,
  onValueChange,
  onReasonChange,
  onReviewerNoteChange,
  onSubmit,
  onRefreshFeedback,
}: FeedbackPanelProps) {
  const disabled = isSubmittingFeedback || actionResult === null;

  return (
    <section className="review-section result-adjacent-review">
      <div className="review-section-header">
        <h3>7. Submit feedback on current output</h3>
        <button
          type="button"
          className="button"
          onClick={onRefreshFeedback}
          disabled={isFeedbackLoading || isSubmittingFeedback}
        >
          {isFeedbackLoading ? "Refreshing feedback..." : "Refresh feedback"}
        </button>
      </div>

      <form className="review-form" onSubmit={onSubmit}>
        <p className="review-label">Feedback value</p>
        <div className="review-choice-row">
          <button
            type="button"
            className={feedbackValue === "positive" ? "button review-choice-positive-active" : "button"}
            onClick={() => onValueChange("positive")}
            disabled={disabled}
          >
            Thumbs up
          </button>
          <button
            type="button"
            className={feedbackValue === "negative" ? "button review-choice-negative-active" : "button"}
            onClick={() => onValueChange("negative")}
            disabled={disabled}
          >
            Thumbs down
          </button>
        </div>

        <label htmlFor="feedback-reason-input" className="review-label">
          Reason {feedbackValue === "negative" ? "(required)" : "(optional)"}
        </label>
        <textarea
          id="feedback-reason-input"
          className="review-textarea"
          value={feedbackReason}
          onChange={(event) => onReasonChange(event.target.value)}
          placeholder="Why this output was good or problematic."
          rows={2}
          disabled={disabled}
        />

        <label htmlFor="feedback-note-input" className="review-label">
          Reviewer note (optional)
        </label>
        <textarea
          id="feedback-note-input"
          className="review-textarea"
          value={feedbackReviewerNote}
          onChange={(event) => onReviewerNoteChange(event.target.value)}
          placeholder="Additional context for future review."
          rows={2}
          disabled={disabled}
        />

        <div className="review-actions">
          <button type="submit" className="button" disabled={disabled}>
            {isSubmittingFeedback ? "Saving feedback..." : "Save feedback"}
          </button>
        </div>
      </form>

      {actionResult === null ? (
        <p className="empty-hint">Run a research action to enable feedback submission.</p>
      ) : null}

      {feedbackSubmitErrorMessage ? (
        <section className="error-panel">
          <p>Could not save feedback: {feedbackSubmitErrorMessage}</p>
        </section>
      ) : null}

      {feedbackSubmitStatusMessage ? (
        <p className="review-success-text">{feedbackSubmitStatusMessage}</p>
      ) : null}

      <div className="review-history">
        <h4>Recent feedback</h4>

        {isFeedbackLoading ? <p className="inline-loading">Loading feedback...</p> : null}

        {!isFeedbackLoading && feedbackLoadErrorMessage ? (
          <section className="error-panel">
            <p>Could not load feedback: {feedbackLoadErrorMessage}</p>
            <button
              type="button"
              className="button"
              onClick={onRefreshFeedback}
              disabled={isSubmittingFeedback}
            >
              Retry feedback
            </button>
          </section>
        ) : null}

        {!isFeedbackLoading && !feedbackLoadErrorMessage && feedbackRecords.length === 0 ? (
          <p className="empty-hint">No feedback has been recorded for this document yet.</p>
        ) : null}

        {!isFeedbackLoading && !feedbackLoadErrorMessage && feedbackRecords.length > 0 ? (
          <div className="feedback-list">
            {feedbackRecords.map((record) => (
              <article key={record.id} className="feedback-card">
                <header className="feedback-meta">
                  <span>#{record.id}</span>
                  <span>{record.workflow_type}</span>
                  <span
                    className={
                      record.feedback_value === "positive"
                        ? "feedback-value-pill positive"
                        : "feedback-value-pill negative"
                    }
                  >
                    {record.feedback_value}
                  </span>
                  <span title={record.created_at}>{formatCreatedAt(record.created_at)}</span>
                </header>
                {record.target_reference ? (
                  <p className="feedback-detail">target_reference: {record.target_reference}</p>
                ) : null}
                {record.reason ? (
                  <p className="feedback-detail">reason: {record.reason}</p>
                ) : null}
                {record.reviewer_note ? (
                  <p className="feedback-detail">reviewer_note: {record.reviewer_note}</p>
                ) : null}
              </article>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}
