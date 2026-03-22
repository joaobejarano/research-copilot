import { requestJson } from "./client";
import type {
  AskGroundedQuestionRequestModel,
  AskGroundedQuestionResponseModel,
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
