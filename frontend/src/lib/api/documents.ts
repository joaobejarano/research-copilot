import { ApiClientError, requestJson } from "./client";
import { getApiBaseUrl } from "../config/env";
import type {
  AskGroundedQuestionRequestModel,
  AskGroundedQuestionResponseModel,
  BuildTimelineRequestModel,
  BuildTimelineResponseModel,
  ExtractKpisRequestModel,
  ExtractKpisResponseModel,
  ExtractRisksRequestModel,
  ExtractRisksResponseModel,
  GenerateMemoRequestModel,
  GenerateMemoResponseModel,
  GetDocumentChunksRequestModel,
  GetDocumentChunksResponseModel,
  GetDocumentDetailRequestModel,
  GetDocumentDetailResponseModel,
  ListDocumentsRequestModel,
  ListDocumentsResponseModel,
  ProcessDocumentRequestModel,
  ProcessDocumentResponseModel,
  WorkflowStreamEvent
} from "./models/documents";

export async function listDocuments(
  _request: ListDocumentsRequestModel = {}
): Promise<ListDocumentsResponseModel> {
  return requestJson<ListDocumentsResponseModel>("/documents", { method: "GET" });
}

export async function getDocumentDetail(
  request: GetDocumentDetailRequestModel
): Promise<GetDocumentDetailResponseModel> {
  return requestJson<GetDocumentDetailResponseModel>(`/documents/${request.documentId}`, {
    method: "GET"
  });
}

export async function processDocument(
  request: ProcessDocumentRequestModel
): Promise<ProcessDocumentResponseModel> {
  return requestJson<ProcessDocumentResponseModel>(`/documents/${request.documentId}/process`, {
    method: "POST"
  });
}

export async function getDocumentChunks(
  request: GetDocumentChunksRequestModel
): Promise<GetDocumentChunksResponseModel> {
  return requestJson<GetDocumentChunksResponseModel>(`/documents/${request.documentId}/chunks`, {
    method: "GET"
  });
}

export async function askGroundedQuestion(
  request: AskGroundedQuestionRequestModel
): Promise<AskGroundedQuestionResponseModel> {
  const { documentId, ...body } = request;

  return requestJson<AskGroundedQuestionResponseModel>(`/documents/${documentId}/ask`, {
    method: "POST",
    body
  });
}

export async function generateMemo(
  request: GenerateMemoRequestModel
): Promise<GenerateMemoResponseModel> {
  return requestJson<GenerateMemoResponseModel>(`/documents/${request.documentId}/memo`, {
    method: "POST"
  });
}

export async function extractKpis(
  request: ExtractKpisRequestModel
): Promise<ExtractKpisResponseModel> {
  return requestJson<ExtractKpisResponseModel>(`/documents/${request.documentId}/extract/kpis`, {
    method: "POST"
  });
}

export async function extractRisks(
  request: ExtractRisksRequestModel
): Promise<ExtractRisksResponseModel> {
  return requestJson<ExtractRisksResponseModel>(`/documents/${request.documentId}/extract/risks`, {
    method: "POST"
  });
}

export async function buildTimeline(
  request: BuildTimelineRequestModel
): Promise<BuildTimelineResponseModel> {
  return requestJson<BuildTimelineResponseModel>(`/documents/${request.documentId}/timeline`, {
    method: "POST"
  });
}

// ------------------------------------------------------------------ //
// Streaming variants — yields WorkflowStreamEvent from SSE endpoints  //
// ------------------------------------------------------------------ //

async function* parseSSEStream(body: ReadableStream<Uint8Array>): AsyncGenerator<WorkflowStreamEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";

      for (const part of parts) {
        for (const line of part.split("\n")) {
          const trimmed = line.trim();
          if (trimmed.startsWith("data: ")) {
            try {
              yield JSON.parse(trimmed.slice(6)) as WorkflowStreamEvent;
            } catch {
              // skip malformed SSE events
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

async function openSSEStream(path: string): Promise<ReadableStream<Uint8Array>> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "POST",
    cache: "no-store"
  });

  if (!response.ok) {
    let detail = response.statusText || "Stream request failed.";
    try {
      const payload = (await response.json()) as { detail?: string };
      if (typeof payload.detail === "string" && payload.detail.length > 0) {
        detail = payload.detail;
      }
    } catch {
      // ignore JSON parse errors on error responses
    }
    throw new ApiClientError(response.status, detail);
  }

  if (!response.body) {
    throw new ApiClientError(500, "Response body was empty.");
  }

  return response.body;
}

export async function* streamMemo(documentId: number): AsyncGenerator<WorkflowStreamEvent> {
  const body = await openSSEStream(`/documents/${documentId}/memo/stream`);
  yield* parseSSEStream(body);
}

export async function* streamKpis(documentId: number): AsyncGenerator<WorkflowStreamEvent> {
  const body = await openSSEStream(`/documents/${documentId}/extract/kpis/stream`);
  yield* parseSSEStream(body);
}

export async function* streamRisks(documentId: number): AsyncGenerator<WorkflowStreamEvent> {
  const body = await openSSEStream(`/documents/${documentId}/extract/risks/stream`);
  yield* parseSSEStream(body);
}

export async function* streamTimeline(documentId: number): AsyncGenerator<WorkflowStreamEvent> {
  const body = await openSSEStream(`/documents/${documentId}/timeline/stream`);
  yield* parseSSEStream(body);
}
