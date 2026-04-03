import { requestJson } from "./client";
import type {
  CreateFeedbackRequestModel,
  CreateFeedbackResponseModel,
  ListFeedbackRequestModel,
  ListFeedbackResponseModel
} from "./models/feedback";

function buildFeedbackQuery(request: ListFeedbackRequestModel): string {
  const searchParams = new URLSearchParams();

  if (request.workflow_type !== undefined) {
    searchParams.set("workflow_type", request.workflow_type);
  }
  if (request.document_id !== undefined) {
    searchParams.set("document_id", String(request.document_id));
  }
  if (request.feedback_value !== undefined) {
    searchParams.set("feedback_value", request.feedback_value);
  }
  if (request.limit !== undefined) {
    searchParams.set("limit", String(request.limit));
  }

  const queryString = searchParams.toString();
  return queryString.length > 0 ? `?${queryString}` : "";
}

export async function createFeedback(
  request: CreateFeedbackRequestModel
): Promise<CreateFeedbackResponseModel> {
  return requestJson<CreateFeedbackResponseModel>("/feedback", {
    method: "POST",
    body: request
  });
}

export async function listFeedback(
  request: ListFeedbackRequestModel = {}
): Promise<ListFeedbackResponseModel> {
  const query = buildFeedbackQuery(request);
  return requestJson<ListFeedbackResponseModel>(`/feedback${query}`, { method: "GET" });
}
