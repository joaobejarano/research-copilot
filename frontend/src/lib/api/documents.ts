import { requestJson } from "./client";
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
  ProcessDocumentResponseModel
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
