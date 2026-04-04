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

export interface GenerateMemoRequestModel {
  documentId: number;
}

export interface MemoCitationsBySectionModel {
  company_overview: string[];
  key_developments: string[];
  risks: string[];
  catalysts: string[];
  kpis: string[];
  open_questions: string[];
}

export interface MemoDraftModel {
  company_overview: string;
  key_developments: string[];
  risks: string[];
  catalysts: string[];
  kpis: string[];
  open_questions: string[];
  citations_by_section: MemoCitationsBySectionModel;
}

export interface GenerateMemoResponseModel {
  document_id: number;
  status: "generated" | "insufficient_evidence";
  memo: MemoDraftModel | null;
}

export interface WorkflowEvidenceModel {
  citations: GroundedCitationModel[];
}

export interface ExtractKpisRequestModel {
  documentId: number;
}

export interface KpiItemModel {
  name: string;
  value: string;
  unit: string | null;
  period: string | null;
  citation: string;
}

export interface ExtractKpisResponseModel {
  workflow: "kpi_extraction";
  document_id: number;
  status: "completed" | "insufficient_evidence";
  kpis: KpiItemModel[];
  evidence: WorkflowEvidenceModel;
}

export interface ExtractRisksRequestModel {
  documentId: number;
}

export interface RiskItemModel {
  title: string;
  description: string;
  severity_or_materiality: "low" | "medium" | "high" | "critical" | "unknown";
  citation: string;
}

export interface ExtractRisksResponseModel {
  workflow: "risk_extraction";
  document_id: number;
  status: "completed" | "insufficient_evidence";
  risks: RiskItemModel[];
  evidence: WorkflowEvidenceModel;
}

export interface BuildTimelineRequestModel {
  documentId: number;
}

export interface TimelineEventModel {
  event_date_or_period: string;
  event_summary: string;
  citation: string;
}

export interface BuildTimelineResponseModel {
  workflow: "timeline_building";
  document_id: number;
  status: "completed" | "insufficient_evidence";
  events: TimelineEventModel[];
  evidence: WorkflowEvidenceModel;
}

export type WorkflowStreamEvent =
  | { type: "status"; step: "retrieving" | "generating"; message: string }
  | { type: "result"; payload: unknown }
  | { type: "error"; message: string };
