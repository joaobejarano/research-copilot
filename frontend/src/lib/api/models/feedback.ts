export type FeedbackWorkflowType =
  | "ask"
  | "memo"
  | "extract_kpis"
  | "extract_risks"
  | "timeline"
  | "agent";

export type FeedbackValue = "positive" | "negative";

export interface FeedbackRecordModel {
  id: number;
  workflow_type: FeedbackWorkflowType;
  document_id: number;
  target_id: number | null;
  target_reference: string | null;
  feedback_value: FeedbackValue;
  reason: string | null;
  reviewer_note: string | null;
  created_at: string;
}

export interface CreateFeedbackRequestModel {
  workflow_type: FeedbackWorkflowType;
  document_id: number;
  target_id?: number;
  target_reference?: string;
  feedback_value: FeedbackValue;
  reason?: string;
  reviewer_note?: string;
}

export type CreateFeedbackResponseModel = FeedbackRecordModel;

export interface ListFeedbackRequestModel {
  workflow_type?: FeedbackWorkflowType;
  document_id?: number;
  feedback_value?: FeedbackValue;
  limit?: number;
}

export type ListFeedbackResponseModel = FeedbackRecordModel[];
