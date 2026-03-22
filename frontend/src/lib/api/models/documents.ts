export interface DocumentStatusModel {
  id: number;
  company_name: string;
  document_type: string;
  period: string;
  source_filename: string;
  storage_path: string;
  status: string;
  created_at: string;
}

export interface ListDocumentsRequestModel {}

export type ListDocumentsResponseModel = DocumentStatusModel[];

export interface GetDocumentDetailRequestModel {
  documentId: number;
}

export type GetDocumentDetailResponseModel = DocumentStatusModel;

export interface ProcessDocumentRequestModel {
  documentId: number;
}

export interface ProcessDocumentResponseModel {
  document_id: number;
  status: string;
  chunk_count: number;
}

export interface DocumentChunkModel {
  chunk_index: number;
  page_number: number | null;
  text: string;
  token_count: number;
}

export interface GetDocumentChunksRequestModel {
  documentId: number;
}

export interface GetDocumentChunksResponseModel {
  document_id: number;
  status: string;
  chunk_count: number;
  embedding_dimension: number;
  chunks: DocumentChunkModel[];
}

export interface AskGroundedQuestionRequestModel {
  documentId: number;
  question: string;
  top_k?: number;
  min_similarity?: number;
}

export interface GroundedCitationModel {
  citation_id: string;
  rank: number;
  document_id: number;
  chunk_index: number;
  page_number: number | null;
  text_excerpt: string;
  retrieval_score: number;
}

export interface AskGroundedQuestionResponseModel {
  question: string;
  answer: string;
  status: "answered" | "insufficient_evidence";
  citations: GroundedCitationModel[];
}
