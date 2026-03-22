"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiClientError } from "../../lib/api/client";
import { getDocumentDetail, listDocuments, processDocument } from "../../lib/api/documents";
import type {
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

    void loadSelectedDocumentDetail();

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
    } finally {
      setIsProcessing(false);
    }
  }

  const shouldShowChunkCount =
    selectedDocumentDetail !== null &&
    lastProcessedDocumentId === selectedDocumentDetail.id &&
    lastProcessChunkCount !== null;

  return (
    <main className="container dashboard-container">
      <header className="dashboard-header">
        <div>
          <h1>Documents</h1>
          <p>Analyst dashboard document list.</p>
        </div>
        <Link href="/">Back to home</Link>
      </header>

      {isLoading ? <p>Loading documents...</p> : null}

      {!isLoading && errorMessage ? (
        <section className="error-panel">
          <p>Could not load documents: {errorMessage}</p>
          <button type="button" className="button" onClick={() => void loadDocuments()}>
            Retry
          </button>
        </section>
      ) : null}

      {!isLoading && !errorMessage && documents.length === 0 ? (
        <p>No documents found.</p>
      ) : null}

      {!isLoading && !errorMessage && documents.length > 0 ? (
        <>
          <section className="document-detail-panel">
            <h2>Document detail</h2>

            {selectedDocumentId === null ? <p>Select a document from the list.</p> : null}

            {selectedDocumentId !== null && isDetailLoading ? <p>Loading selected document...</p> : null}

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
              </>
            ) : null}
          </section>

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
        </>
      ) : null}
    </main>
  );
}
