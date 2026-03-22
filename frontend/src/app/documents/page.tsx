"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";
import { ApiClientError } from "../../lib/api/client";
import {
  askGroundedQuestion,
  getDocumentChunks,
  getDocumentDetail,
  listDocuments,
  processDocument
} from "../../lib/api/documents";
import type {
  AskGroundedQuestionResponseModel,
  DocumentChunkModel,
  DocumentStatusModel,
  GetDocumentDetailResponseModel
} from "../../lib/api/models/documents";

function formatCreatedAt(createdAt: string): string {
  const parsedDate = new Date(createdAt);
  if (Number.isNaN(parsedDate.getTime())) {
    return createdAt;
  }
  return parsedDate.toLocaleString();
}

function toErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.detail;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unknown error.";
}

function replaceDocumentInList(
  currentDocuments: DocumentStatusModel[],
  nextDocument: DocumentStatusModel
): DocumentStatusModel[] {
  return currentDocuments.map((document) =>
    document.id === nextDocument.id ? nextDocument : document
  );
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentStatusModel[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedDocumentDetail, setSelectedDocumentDetail] =
    useState<GetDocumentDetailResponseModel | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState<boolean>(false);
  const [detailErrorMessage, setDetailErrorMessage] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [processingErrorMessage, setProcessingErrorMessage] = useState<string | null>(null);
  const [processingStatusMessage, setProcessingStatusMessage] = useState<string | null>(null);
  const [lastProcessedDocumentId, setLastProcessedDocumentId] = useState<number | null>(null);
  const [lastProcessChunkCount, setLastProcessChunkCount] = useState<number | null>(null);
  const [documentChunks, setDocumentChunks] = useState<DocumentChunkModel[]>([]);
  const [chunksCountFromApi, setChunksCountFromApi] = useState<number | null>(null);
  const [isChunksLoading, setIsChunksLoading] = useState<boolean>(false);
  const [chunksErrorMessage, setChunksErrorMessage] = useState<string | null>(null);
  const [questionInput, setQuestionInput] = useState<string>("");
  const [isAskingQuestion, setIsAskingQuestion] = useState<boolean>(false);
  const [askErrorMessage, setAskErrorMessage] = useState<string | null>(null);
  const [askResult, setAskResult] = useState<AskGroundedQuestionResponseModel | null>(null);

  async function loadDocuments(): Promise<void> {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const fetchedDocuments = await listDocuments();
      setDocuments(fetchedDocuments);
      setSelectedDocumentId((currentSelection) => {
        if (fetchedDocuments.length === 0) {
          return null;
        }
        if (
          currentSelection !== null &&
          fetchedDocuments.some((document) => document.id === currentSelection)
        ) {
          return currentSelection;
        }
        return fetchedDocuments[0].id;
      });
    } catch (error) {
      setErrorMessage(toErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadDocuments();
  }, []);

  useEffect(() => {
    if (selectedDocumentId === null) {
      setSelectedDocumentDetail(null);
      setIsDetailLoading(false);
      setDetailErrorMessage(null);
      setProcessingErrorMessage(null);
      setProcessingStatusMessage(null);
      setLastProcessedDocumentId(null);
      setLastProcessChunkCount(null);
      setDocumentChunks([]);
      setChunksCountFromApi(null);
      setIsChunksLoading(false);
      setChunksErrorMessage(null);
      setQuestionInput("");
      setIsAskingQuestion(false);
      setAskErrorMessage(null);
      setAskResult(null);
      return;
    }

    const documentId = selectedDocumentId;
    let isCancelled = false;

    async function loadSelectedDocumentDetail(): Promise<void> {
      setIsDetailLoading(true);
      setDetailErrorMessage(null);
      setProcessingErrorMessage(null);
      setProcessingStatusMessage(null);
      setLastProcessedDocumentId(null);
      setLastProcessChunkCount(null);
      setSelectedDocumentDetail(null);

      try {
        const fetchedDetail = await getDocumentDetail({ documentId });
        if (isCancelled) {
          return;
        }
        setSelectedDocumentDetail(fetchedDetail);
        setDocuments((currentDocuments) => replaceDocumentInList(currentDocuments, fetchedDetail));
      } catch (error) {
        if (isCancelled) {
          return;
        }
        setDetailErrorMessage(toErrorMessage(error));
      } finally {
        if (!isCancelled) {
          setIsDetailLoading(false);
        }
      }
    }

    async function loadSelectedDocumentChunks(): Promise<void> {
      setIsChunksLoading(true);
      setChunksErrorMessage(null);
      setDocumentChunks([]);
      setChunksCountFromApi(null);
      setQuestionInput("");
      setIsAskingQuestion(false);
      setAskErrorMessage(null);
      setAskResult(null);

      try {
        const chunksResponse = await getDocumentChunks({ documentId });
        if (isCancelled) {
          return;
        }

        const orderedChunks = [...chunksResponse.chunks].sort(
          (leftChunk, rightChunk) => leftChunk.chunk_index - rightChunk.chunk_index
        );

        setDocumentChunks(orderedChunks);
        setChunksCountFromApi(chunksResponse.chunk_count);
      } catch (error) {
        if (isCancelled) {
          return;
        }
        setChunksErrorMessage(toErrorMessage(error));
      } finally {
        if (!isCancelled) {
          setIsChunksLoading(false);
        }
      }
    }

    void loadSelectedDocumentDetail();
    void loadSelectedDocumentChunks();

    return () => {
      isCancelled = true;
    };
  }, [selectedDocumentId]);

  async function refreshSelectedDocumentDetail(): Promise<void> {
    if (selectedDocumentId === null) {
      return;
    }

    setIsDetailLoading(true);
    setDetailErrorMessage(null);

    try {
      const refreshedDetail = await getDocumentDetail({ documentId: selectedDocumentId });
      setSelectedDocumentDetail(refreshedDetail);
      setDocuments((currentDocuments) => replaceDocumentInList(currentDocuments, refreshedDetail));
    } catch (error) {
      setSelectedDocumentDetail(null);
      setDetailErrorMessage(toErrorMessage(error));
    } finally {
      setIsDetailLoading(false);
    }
  }

  async function refreshSelectedDocumentChunks(): Promise<void> {
    if (selectedDocumentId === null) {
      return;
    }

    setIsChunksLoading(true);
    setChunksErrorMessage(null);

    try {
      const chunksResponse = await getDocumentChunks({ documentId: selectedDocumentId });
      const orderedChunks = [...chunksResponse.chunks].sort(
        (leftChunk, rightChunk) => leftChunk.chunk_index - rightChunk.chunk_index
      );
      setDocumentChunks(orderedChunks);
      setChunksCountFromApi(chunksResponse.chunk_count);
    } catch (error) {
      setDocumentChunks([]);
      setChunksCountFromApi(null);
      setChunksErrorMessage(toErrorMessage(error));
    } finally {
      setIsChunksLoading(false);
    }
  }

  async function handleProcessDocument(): Promise<void> {
    if (!selectedDocumentDetail || isProcessing) {
      return;
    }

    const documentId = selectedDocumentDetail.id;
    const previousStatus = selectedDocumentDetail.status;

    setIsProcessing(true);
    setProcessingErrorMessage(null);
    setProcessingStatusMessage(`Status transition: ${previousStatus} -> processing`);
    setLastProcessedDocumentId(null);
    setLastProcessChunkCount(null);

    setSelectedDocumentDetail((currentDetail) =>
      currentDetail && currentDetail.id === documentId
        ? { ...currentDetail, status: "processing" }
        : currentDetail
    );
    setDocuments((currentDocuments) =>
      currentDocuments.map((document) =>
        document.id === documentId ? { ...document, status: "processing" } : document
      )
    );

    try {
      const processResult = await processDocument({ documentId });
      setProcessingStatusMessage(
        `Status transition: ${previousStatus} -> processing -> ${processResult.status}`
      );
      setLastProcessedDocumentId(processResult.document_id);
      setLastProcessChunkCount(processResult.chunk_count);

      const refreshedDetail = await getDocumentDetail({ documentId });
      setSelectedDocumentDetail(refreshedDetail);
      setDocuments((currentDocuments) => replaceDocumentInList(currentDocuments, refreshedDetail));
      await refreshSelectedDocumentChunks();
    } catch (error) {
      setProcessingErrorMessage(toErrorMessage(error));
      setProcessingStatusMessage(`Status transition: ${previousStatus} -> processing -> failed`);

      try {
        const refreshedDetail = await getDocumentDetail({ documentId });
        setSelectedDocumentDetail(refreshedDetail);
        setDocuments((currentDocuments) =>
          replaceDocumentInList(currentDocuments, refreshedDetail)
        );
      } catch {
        // Keep the last known detail when refresh fails after processing.
      }

      await refreshSelectedDocumentChunks();
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleAskQuestion(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();

    if (selectedDocumentId === null || isAskingQuestion) {
      return;
    }

    const normalizedQuestion = questionInput.trim();
    if (normalizedQuestion.length === 0) {
      setAskErrorMessage("Question is required.");
      return;
    }

    setIsAskingQuestion(true);
    setAskErrorMessage(null);

    try {
      const askResponse = await askGroundedQuestion({
        documentId: selectedDocumentId,
        question: normalizedQuestion
      });
      setAskResult(askResponse);
    } catch (error) {
      setAskResult(null);
      setAskErrorMessage(toErrorMessage(error));
    } finally {
      setIsAskingQuestion(false);
    }
  }

  const shouldShowChunkCount =
    selectedDocumentDetail !== null &&
    lastProcessedDocumentId === selectedDocumentDetail.id &&
    lastProcessChunkCount !== null;
  const readyDocumentsCount = documents.filter((document) => document.status === "ready").length;
  const selectedDocumentSummary =
    selectedDocumentId === null
      ? null
      : documents.find((document) => document.id === selectedDocumentId) ?? null;

  return (
    <main className="container dashboard-container">
      <header className="dashboard-header">
        <div>
          <h1>Documents</h1>
          <p>Analyst dashboard document list.</p>
        </div>
        <Link href="/">Back to home</Link>
      </header>

      <section className="dashboard-summary">
        <article className="summary-card">
          <p className="summary-label">documents</p>
          <p className="summary-value">{documents.length}</p>
        </article>
        <article className="summary-card">
          <p className="summary-label">ready</p>
          <p className="summary-value">{readyDocumentsCount}</p>
        </article>
        <article className="summary-card">
          <p className="summary-label">selected</p>
          <p className="summary-value">
            {selectedDocumentSummary ? `#${selectedDocumentSummary.id}` : "none"}
          </p>
        </article>
      </section>

      {isLoading ? (
        <section className="state-panel">
          <p className="state-title">Loading documents...</p>
          <p>Fetching dashboard data from the API.</p>
        </section>
      ) : null}

      {!isLoading && errorMessage ? (
        <section className="error-panel">
          <p>Could not load documents: {errorMessage}</p>
          <button type="button" className="button" onClick={() => void loadDocuments()}>
            Retry
          </button>
        </section>
      ) : null}

      {!isLoading && !errorMessage && documents.length === 0 ? (
        <section className="state-panel">
          <p className="state-title">No documents yet</p>
          <p>Upload a document through the API to start inspecting details, chunks, and grounded Q&A.</p>
        </section>
      ) : null}

      {!isLoading && !errorMessage && documents.length > 0 ? (
        <>
          <section className="document-detail-panel">
            <h2>Document detail</h2>
            <p className="section-note">
              Select a document to inspect metadata, processing status, grounded Q&A, and chunks.
            </p>

            {selectedDocumentId === null ? (
              <section className="state-panel compact">
                <p className="state-title">No document selected</p>
                <p>Choose a row from the documents table below.</p>
              </section>
            ) : null}

            {selectedDocumentId !== null && isDetailLoading ? (
              <p className="inline-loading">Loading selected document...</p>
            ) : null}

            {selectedDocumentId !== null && !isDetailLoading && detailErrorMessage ? (
              <section className="error-panel">
                <p>Could not load selected document: {detailErrorMessage}</p>
                <button
                  type="button"
                  className="button"
                  onClick={() => void refreshSelectedDocumentDetail()}
                >
                  Retry detail
                </button>
              </section>
            ) : null}

            {selectedDocumentId !== null &&
            !isDetailLoading &&
            !detailErrorMessage &&
            selectedDocumentDetail ? (
              <>
                <dl className="document-detail-grid">
                  <div className="document-detail-item">
                    <dt>id</dt>
                    <dd>{selectedDocumentDetail.id}</dd>
                  </div>
                  <div className="document-detail-item">
                    <dt>company_name</dt>
                    <dd>{selectedDocumentDetail.company_name}</dd>
                  </div>
                  <div className="document-detail-item">
                    <dt>document_type</dt>
                    <dd>{selectedDocumentDetail.document_type}</dd>
                  </div>
                  <div className="document-detail-item">
                    <dt>period</dt>
                    <dd>{selectedDocumentDetail.period}</dd>
                  </div>
                  <div className="document-detail-item">
                    <dt>source_filename</dt>
                    <dd>{selectedDocumentDetail.source_filename}</dd>
                  </div>
                  <div className="document-detail-item">
                    <dt>storage_path</dt>
                    <dd>{selectedDocumentDetail.storage_path}</dd>
                  </div>
                  <div className="document-detail-item">
                    <dt>status</dt>
                    <dd>{selectedDocumentDetail.status}</dd>
                  </div>
                  <div className="document-detail-item">
                    <dt>created_at</dt>
                    <dd title={selectedDocumentDetail.created_at}>
                      {formatCreatedAt(selectedDocumentDetail.created_at)}
                    </dd>
                  </div>
                </dl>

                <p className="status-transition">
                  {processingStatusMessage ??
                    `Current status: ${selectedDocumentDetail.status}`}
                </p>

                {shouldShowChunkCount ? (
                  <p className="chunk-count-text">chunk_count: {lastProcessChunkCount}</p>
                ) : null}

                <div className="document-actions">
                  {selectedDocumentDetail.status !== "ready" ? (
                    <button
                      type="button"
                      className="button"
                      onClick={() => void handleProcessDocument()}
                      disabled={isProcessing}
                    >
                      {isProcessing ? "Processing..." : "Process document"}
                    </button>
                  ) : (
                    <p className="ready-text">Document is ready.</p>
                  )}

                  <button
                    type="button"
                    className="button"
                    onClick={() => void refreshSelectedDocumentDetail()}
                    disabled={isProcessing || isDetailLoading}
                  >
                    Refresh detail
                  </button>
                </div>

                {isProcessing ? <p className="processing-text">Processing document...</p> : null}

                {processingErrorMessage ? (
                  <section className="error-panel">
                    <p>Document processing failed: {processingErrorMessage}</p>
                  </section>
                ) : null}

                <section className="qa-section">
                  <div className="qa-section-header">
                    <h3>Grounded Q&A</h3>
                  </div>

                  <form className="qa-form" onSubmit={(event) => void handleAskQuestion(event)}>
                    <label htmlFor="grounded-question-input" className="qa-label">
                      Ask a question about this document
                    </label>
                    <textarea
                      id="grounded-question-input"
                      className="qa-input"
                      value={questionInput}
                      onChange={(event) => setQuestionInput(event.target.value)}
                      placeholder="Example: What changed in revenue this quarter?"
                      rows={3}
                      disabled={isAskingQuestion || isProcessing || isDetailLoading}
                    />
                    <div className="qa-actions">
                      <button
                        type="submit"
                        className="button"
                        disabled={
                          isAskingQuestion ||
                          isProcessing ||
                          isDetailLoading ||
                          questionInput.trim().length === 0
                        }
                      >
                        {isAskingQuestion ? "Asking..." : "Ask question"}
                      </button>
                    </div>
                  </form>

                  {isAskingQuestion ? <p>Generating grounded answer...</p> : null}

                  {askErrorMessage ? (
                    <section className="error-panel">
                      <p>Grounded Q&A failed: {askErrorMessage}</p>
                    </section>
                  ) : null}

                  {askResult ? (
                    <section className="qa-result-card">
                      <div className="qa-status-row">
                        <span className="qa-status-label">status:</span>
                        <span
                          className={
                            askResult.status === "answered"
                              ? "qa-status-badge answered"
                              : "qa-status-badge insufficient"
                          }
                        >
                          {askResult.status}
                        </span>
                      </div>

                      <div className="qa-result-block">
                        <p className="qa-result-title">question</p>
                        <p className="qa-result-text">{askResult.question}</p>
                      </div>

                      <div className="qa-result-block">
                        <p className="qa-result-title">answer</p>
                        <p className="qa-result-text">{askResult.answer}</p>
                      </div>

                      <div className="qa-result-block">
                        <p className="qa-result-title">citations</p>
                        {askResult.citations.length === 0 ? (
                          <p className="qa-result-text">No citations returned.</p>
                        ) : (
                          <div className="citations-list">
                            {[...askResult.citations]
                              .sort((leftCitation, rightCitation) => leftCitation.rank - rightCitation.rank)
                              .map((citation) => (
                                <article key={citation.citation_id} className="citation-card">
                                  <header className="citation-meta">
                                    <span>{citation.citation_id}</span>
                                    <span>rank: {citation.rank}</span>
                                    <span>document_id: {citation.document_id}</span>
                                    <span>chunk_index: {citation.chunk_index}</span>
                                    <span>
                                      page_number:{" "}
                                      {citation.page_number === null ? "null" : citation.page_number}
                                    </span>
                                    <span>
                                      retrieval_score: {citation.retrieval_score.toFixed(3)}
                                    </span>
                                  </header>
                                  <div className="citation-text">{citation.text_excerpt}</div>
                                </article>
                              ))}
                          </div>
                        )}
                      </div>
                    </section>
                  ) : !isAskingQuestion && !askErrorMessage ? (
                    <p className="empty-hint">
                      Submit a question to see a grounded answer with citations.
                    </p>
                  ) : null}
                </section>

                <section className="chunks-section">
                  <div className="chunks-section-header">
                    <h3>Chunks</h3>
                    <button
                      type="button"
                      className="button"
                      onClick={() => void refreshSelectedDocumentChunks()}
                      disabled={isChunksLoading || isProcessing || isDetailLoading}
                    >
                      {isChunksLoading ? "Refreshing chunks..." : "Refresh chunks"}
                    </button>
                  </div>

                  {isChunksLoading ? <p className="inline-loading">Loading chunks...</p> : null}

                  {!isChunksLoading && chunksErrorMessage ? (
                    <section className="error-panel">
                      <p>Could not load chunks: {chunksErrorMessage}</p>
                      <button
                        type="button"
                        className="button"
                        onClick={() => void refreshSelectedDocumentChunks()}
                        disabled={isProcessing || isDetailLoading}
                      >
                        Retry chunks
                      </button>
                    </section>
                  ) : null}

                  {!isChunksLoading && !chunksErrorMessage && chunksCountFromApi !== null ? (
                    <p className="chunk-count-text">chunks_count: {chunksCountFromApi}</p>
                  ) : null}

                  {!isChunksLoading && !chunksErrorMessage && documentChunks.length === 0 ? (
                    <p className="empty-hint">No chunks available for this document.</p>
                  ) : null}

                  {!isChunksLoading && !chunksErrorMessage && documentChunks.length > 0 ? (
                    <div className="chunks-list">
                      {documentChunks.map((chunk) => (
                        <article key={chunk.chunk_index} className="chunk-card">
                          <header className="chunk-meta">
                            <span>chunk_index: {chunk.chunk_index}</span>
                            <span>
                              page_number: {chunk.page_number === null ? "null" : chunk.page_number}
                            </span>
                            <span>token_count: {chunk.token_count}</span>
                          </header>
                          <div className="chunk-text">{chunk.text}</div>
                        </article>
                      ))}
                    </div>
                  ) : null}
                </section>
              </>
            ) : null}
          </section>

          <section className="documents-table-section">
            <div className="section-header-row">
              <h2>Documents list</h2>
              <p>Select one document at a time.</p>
            </div>

            <section className="documents-table-wrapper">
            <table className="documents-table">
              <thead>
                <tr>
                  <th>select</th>
                  <th>id</th>
                  <th>company_name</th>
                  <th>document_type</th>
                  <th>period</th>
                  <th>status</th>
                  <th>created_at</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((document) => (
                  <tr
                    key={document.id}
                    className={document.id === selectedDocumentId ? "selected-row" : ""}
                  >
                    <td>
                      <button
                        type="button"
                        className="button"
                        onClick={() => setSelectedDocumentId(document.id)}
                        disabled={document.id === selectedDocumentId || isProcessing}
                      >
                        {document.id === selectedDocumentId ? "Selected" : "Select"}
                      </button>
                    </td>
                    <td>{document.id}</td>
                    <td>{document.company_name}</td>
                    <td>{document.document_type}</td>
                    <td>{document.period}</td>
                    <td>{document.status}</td>
                    <td title={document.created_at}>{formatCreatedAt(document.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </section>
          </section>
        </>
      ) : null}
    </main>
  );
}
