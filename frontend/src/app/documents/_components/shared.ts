import { ApiClientError } from "../../../lib/api/client";
import type {
  AskGroundedQuestionResponseModel,
  BuildTimelineResponseModel,
  DocumentStatusModel,
  ExtractKpisResponseModel,
  ExtractRisksResponseModel,
  GenerateMemoResponseModel,
} from "../../../lib/api/models/documents";

export type ResearchActionType = "ask" | "memo" | "extract_kpis" | "extract_risks" | "timeline";

export type ResearchActionResult =
  | { action: "ask"; response: AskGroundedQuestionResponseModel }
  | { action: "memo"; response: GenerateMemoResponseModel }
  | { action: "extract_kpis"; response: ExtractKpisResponseModel }
  | { action: "extract_risks"; response: ExtractRisksResponseModel }
  | { action: "timeline"; response: BuildTimelineResponseModel };

export function formatCreatedAt(createdAt: string): string {
  const parsedDate = new Date(createdAt);
  if (Number.isNaN(parsedDate.getTime())) {
    return createdAt;
  }
  return parsedDate.toLocaleString();
}

export function compactText(value: string, maxLength: number): string {
  return value.trim().replace(/\s+/g, " ").slice(0, maxLength);
}

export function toErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.detail;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unknown error.";
}

export function getStatusTone(status: string): "ready" | "processing" | "failed" | "other" {
  if (status === "ready") return "ready";
  if (status === "processing") return "processing";
  if (status === "failed") return "failed";
  return "other";
}

export function getResultTitle(action: ResearchActionType): string {
  switch (action) {
    case "ask":
      return "Ask";
    case "memo":
      return "Generate memo";
    case "extract_kpis":
      return "Extract KPIs";
    case "extract_risks":
      return "Extract risks";
    case "timeline":
      return "Build timeline";
  }
}

export function getResultStatus(result: ResearchActionResult): string {
  return result.response.status;
}

export function buildResultTargetReference(result: ResearchActionResult): string {
  if (result.action === "ask") {
    return `ask:${result.response.status}:${compactText(result.response.question, 160)}`;
  }
  if (result.action === "memo") {
    const overview = result.response.memo?.company_overview ?? "no_memo";
    return `memo:${result.response.status}:${compactText(overview, 160)}`;
  }
  if (result.action === "extract_kpis") {
    return `extract_kpis:${result.response.status}:count=${result.response.kpis.length}`;
  }
  if (result.action === "extract_risks") {
    return `extract_risks:${result.response.status}:count=${result.response.risks.length}`;
  }
  return `timeline:${result.response.status}:count=${result.response.events.length}`;
}

export function replaceDocumentInList(
  currentDocuments: DocumentStatusModel[],
  nextDocument: DocumentStatusModel
): DocumentStatusModel[] {
  return currentDocuments.map((doc) => (doc.id === nextDocument.id ? nextDocument : doc));
}
