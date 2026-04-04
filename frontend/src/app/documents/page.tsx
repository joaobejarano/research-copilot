"use client";

import Link from "next/link";
import { type FormEvent, type SyntheticEvent, useEffect, useState } from "react";
import { createFeedback, listFeedback } from "../../lib/api/feedback";
import {
  askGroundedQuestion,
  buildTimeline,
  extractKpis,
  extractRisks,
  generateMemo,
  getDocumentChunks,
  getDocumentDetail,
  listDocuments,
  processDocument,
  streamKpis,
  streamMemo,
  streamRisks,
  streamTimeline,
} from "../../lib/api/documents";
import type {
  DocumentChunkModel,
  DocumentStatusModel,
  GetDocumentDetailResponseModel,
} from "../../lib/api/models/documents";
import type { FeedbackRecordModel, FeedbackValue, FeedbackWorkflowType } from "../../lib/api/models/feedback";
import { AdvancedPanel } from "./_components/AdvancedPanel";
import { DocumentHeader } from "./_components/DocumentHeader";
import { DocumentList } from "./_components/DocumentList";
import { FeedbackPanel } from "./_components/FeedbackPanel";
import { ResearchActionsPanel } from "./_components/ResearchActionsPanel";
import { ResultPanel } from "./_components/ResultPanel";
import {
  buildResultTargetReference,
  replaceDocumentInList,
  toErrorMessage,
  type ResearchActionResult,
  type ResearchActionType,
} from "./_components/shared";

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

  const [activeAction, setActiveAction] = useState<ResearchActionType>("ask");
  const [questionInput, setQuestionInput] = useState<string>("");
  const [isActionLoading, setIsActionLoading] = useState<boolean>(false);
  const [actionErrorMessage, setActionErrorMessage] = useState<string | null>(null);
  const [actionResult, setActionResult] = useState<ResearchActionResult | null>(null);
  const [streamingStatusMessage, setStreamingStatusMessage] = useState<string | null>(null);

  const [isAdvancedOpen, setIsAdvancedOpen] = useState<boolean>(false);
  const [documentChunks, setDocumentChunks] = useState<DocumentChunkModel[]>([]);
  const [chunksCountFromApi, setChunksCountFromApi] = useState<number | null>(null);
  const [isChunksLoading, setIsChunksLoading] = useState<boolean>(false);
  const [chunksErrorMessage, setChunksErrorMessage] = useState<string | null>(null);

  const [feedbackValue, setFeedbackValue] = useState<FeedbackValue>("positive");
  const [feedbackReason, setFeedbackReason] = useState<string>("");
  const [feedbackReviewerNote, setFeedbackReviewerNote] = useState<string>("");
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState<boolean>(false);
  const [feedbackSubmitErrorMessage, setFeedbackSubmitErrorMessage] = useState<string | null>(null);
  const [feedbackSubmitStatusMessage, setFeedbackSubmitStatusMessage] = useState<string | null>(null);
  const [feedbackRecords, setFeedbackRecords] = useState<FeedbackRecordModel[]>([]);
  const [isFeedbackLoading, setIsFeedbackLoading] = useState<boolean>(false);
  const [feedbackLoadErrorMessage, setFeedbackLoadErrorMessage] = useState<string | null>(null);

  async function loadDocuments(): Promise<void> {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const fetchedDocuments = await listDocuments();
      setDocuments(fetchedDocuments);
      setSelectedDocumentId((currentSelection) => {
        if (fetchedDocuments.length === 0) return null;
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

      setActiveAction("ask");
      setQuestionInput("");
      setIsActionLoading(false);
      setActionErrorMessage(null);
      setActionResult(null);
      setStreamingStatusMessage(null);

      setIsAdvancedOpen(false);
      setDocumentChunks([]);
      setChunksCountFromApi(null);
      setIsChunksLoading(false);
      setChunksErrorMessage(null);

      setFeedbackValue("positive");
      setFeedbackReason("");
      setFeedbackReviewerNote("");
      setIsSubmittingFeedback(false);
      setFeedbackSubmitErrorMessage(null);
      setFeedbackSubmitStatusMessage(null);
      setFeedbackRecords([]);
      setIsFeedbackLoading(false);
      setFeedbackLoadErrorMessage(null);
      return;
    }

    const documentId = selectedDocumentId;
    let isCancelled = false;

    async function loadSelectedDocumentDetail(): Promise<void> {
      setIsDetailLoading(true);
      setDetailErrorMessage(null);
      setSelectedDocumentDetail(null);
      setProcessingErrorMessage(null);
      setProcessingStatusMessage(null);

      try {
        const fetchedDetail = await getDocumentDetail({ documentId });
        if (isCancelled) return;
        setSelectedDocumentDetail(fetchedDetail);
        setDocuments((currentDocuments) => replaceDocumentInList(currentDocuments, fetchedDetail));
      } catch (error) {
        if (isCancelled) return;
        setDetailErrorMessage(toErrorMessage(error));
      } finally {
        if (!isCancelled) setIsDetailLoading(false);
      }
    }

    async function loadSelectedDocumentFeedback(): Promise<void> {
      setFeedbackValue("positive");
      setFeedbackReason("");
      setFeedbackReviewerNote("");
      setIsSubmittingFeedback(false);
      setFeedbackSubmitErrorMessage(null);
      setFeedbackSubmitStatusMessage(null);
      setFeedbackRecords([]);
      setIsFeedbackLoading(true);
      setFeedbackLoadErrorMessage(null);

      try {
        const feedbackResponse = await listFeedback({ document_id: documentId, limit: 10 });
        if (isCancelled) return;
        setFeedbackRecords(feedbackResponse);
      } catch (error) {
        if (isCancelled) return;
        setFeedbackLoadErrorMessage(toErrorMessage(error));
      } finally {
        if (!isCancelled) setIsFeedbackLoading(false);
      }
    }

    setActiveAction("ask");
    setQuestionInput("");
    setIsActionLoading(false);
    setActionErrorMessage(null);
    setActionResult(null);
    setStreamingStatusMessage(null);

    setIsAdvancedOpen(false);
    setDocumentChunks([]);
    setChunksCountFromApi(null);
    setIsChunksLoading(false);
    setChunksErrorMessage(null);

    void loadSelectedDocumentDetail();
    void loadSelectedDocumentFeedback();

    return () => {
      isCancelled = true;
    };
  }, [selectedDocumentId]);

  async function refreshSelectedDocumentDetail(): Promise<void> {
    if (selectedDocumentId === null) return;

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
    if (selectedDocumentId === null) return;

    setIsChunksLoading(true);
    setChunksErrorMessage(null);

    try {
      const chunksResponse = await getDocumentChunks({ documentId: selectedDocumentId });
      const orderedChunks = [...chunksResponse.chunks].sort(
        (a, b) => a.chunk_index - b.chunk_index
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

  async function refreshSelectedDocumentFeedback(): Promise<void> {
    if (selectedDocumentId === null) return;

    setIsFeedbackLoading(true);
    setFeedbackLoadErrorMessage(null);

    try {
      const feedbackResponse = await listFeedback({ document_id: selectedDocumentId, limit: 10 });
      setFeedbackRecords(feedbackResponse);
    } catch (error) {
      setFeedbackRecords([]);
      setFeedbackLoadErrorMessage(toErrorMessage(error));
    } finally {
      setIsFeedbackLoading(false);
    }
  }

  async function handleProcessDocument(): Promise<void> {
    if (!selectedDocumentDetail || isProcessing) return;

    const documentId = selectedDocumentDetail.id;
    const previousStatus = selectedDocumentDetail.status;

    setIsProcessing(true);
    setProcessingErrorMessage(null);
    setProcessingStatusMessage(`Status transition: ${previousStatus} -> processing`);

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

      const refreshedDetail = await getDocumentDetail({ documentId });
      setSelectedDocumentDetail(refreshedDetail);
      setDocuments((currentDocuments) => replaceDocumentInList(currentDocuments, refreshedDetail));

      setActionErrorMessage(null);
      setActionResult(null);
      setFeedbackSubmitErrorMessage(null);
      setFeedbackSubmitStatusMessage(null);

      setDocumentChunks([]);
      setChunksCountFromApi(null);
      setChunksErrorMessage(null);

      if (isAdvancedOpen) {
        await refreshSelectedDocumentChunks();
      }
    } catch (error) {
      setProcessingErrorMessage(toErrorMessage(error));
      setProcessingStatusMessage(`Status transition: ${previousStatus} -> processing -> failed`);

      try {
        const refreshedDetail = await getDocumentDetail({ documentId });
        setSelectedDocumentDetail(refreshedDetail);
        setDocuments((currentDocuments) => replaceDocumentInList(currentDocuments, refreshedDetail));
      } catch {
        // Keep last known detail when refresh fails.
      }
    } finally {
      setIsProcessing(false);
    }
  }

  async function executeResearchAction(action: ResearchActionType): Promise<void> {
    if (selectedDocumentId === null || isActionLoading) return;

    if (selectedDocumentDetail?.status !== "ready") {
      setActionErrorMessage("Document must be ready before running research actions.");
      return;
    }

    setIsActionLoading(true);
    setActionErrorMessage(null);
    setStreamingStatusMessage(null);

    try {
      let nextResult: ResearchActionResult;

      if (action === "ask") {
        const normalizedQuestion = questionInput.trim();
        if (normalizedQuestion.length === 0) {
          setActionErrorMessage("Question is required for Ask.");
          return;
        }
        nextResult = {
          action: "ask",
          response: await askGroundedQuestion({
            documentId: selectedDocumentId,
            question: normalizedQuestion,
          }),
        };
      } else {
        // Streaming path for the four long-running structured workflows.
        const streamFn =
          action === "memo" ? streamMemo :
          action === "extract_kpis" ? streamKpis :
          action === "extract_risks" ? streamRisks :
          streamTimeline;

        let resultPayload: ResearchActionResult | null = null;

        for await (const event of streamFn(selectedDocumentId)) {
          if (event.type === "status") {
            setStreamingStatusMessage(event.message);
          } else if (event.type === "result") {
            resultPayload = { action, response: event.payload } as ResearchActionResult;
          } else if (event.type === "error") {
            throw new Error(event.message);
          }
        }

        if (resultPayload === null) {
          throw new Error("Stream ended without a result.");
        }
        nextResult = resultPayload;
      }

      setActionResult(nextResult);
      setStreamingStatusMessage(null);
      setFeedbackValue("positive");
      setFeedbackReason("");
      setFeedbackReviewerNote("");
      setFeedbackSubmitErrorMessage(null);
      setFeedbackSubmitStatusMessage(null);
    } catch (error) {
      setActionResult(null);
      setStreamingStatusMessage(null);
      setActionErrorMessage(toErrorMessage(error));
    } finally {
      setIsActionLoading(false);
    }
  }

  async function handleAskSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (activeAction !== "ask") return;
    await executeResearchAction("ask");
  }

  async function handleRunActionButton(): Promise<void> {
    if (activeAction === "ask") return;
    await executeResearchAction(activeAction);
  }

  async function handleSubmitFeedback(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();

    if (selectedDocumentId === null || isSubmittingFeedback) return;

    if (actionResult === null) {
      setFeedbackSubmitErrorMessage("Run a research action first so feedback can be linked.");
      setFeedbackSubmitStatusMessage(null);
      return;
    }

    const normalizedReason = feedbackReason.trim();
    const normalizedReviewerNote = feedbackReviewerNote.trim();

    if (feedbackValue === "negative" && normalizedReason.length === 0) {
      setFeedbackSubmitErrorMessage("Reason is required when feedback is negative.");
      setFeedbackSubmitStatusMessage(null);
      return;
    }

    setIsSubmittingFeedback(true);
    setFeedbackSubmitErrorMessage(null);
    setFeedbackSubmitStatusMessage(null);

    try {
      await createFeedback({
        workflow_type: actionResult.action as FeedbackWorkflowType,
        document_id: selectedDocumentId,
        target_reference: buildResultTargetReference(actionResult),
        feedback_value: feedbackValue,
        reason: feedbackValue === "negative" ? normalizedReason : undefined,
        reviewer_note: normalizedReviewerNote.length > 0 ? normalizedReviewerNote : undefined,
      });

      setFeedbackReason("");
      setFeedbackReviewerNote("");
      setFeedbackSubmitStatusMessage("Feedback saved.");
      await refreshSelectedDocumentFeedback();
    } catch (error) {
      setFeedbackSubmitErrorMessage(toErrorMessage(error));
    } finally {
      setIsSubmittingFeedback(false);
    }
  }

  function handleAdvancedToggle(event: SyntheticEvent<HTMLDetailsElement>): void {
    const nextOpen = event.currentTarget.open;
    setIsAdvancedOpen(nextOpen);

    if (
      nextOpen &&
      selectedDocumentId !== null &&
      !isChunksLoading &&
      documentChunks.length === 0 &&
      chunksErrorMessage === null
    ) {
      void refreshSelectedDocumentChunks();
    }
  }

  const selectedDocumentSummary =
    selectedDocumentId === null
      ? null
      : documents.find((doc) => doc.id === selectedDocumentId) ?? null;

  const selectedStatus =
    selectedDocumentDetail?.status ?? selectedDocumentSummary?.status ?? "unknown";
  const readyDocumentsCount = documents.filter((doc) => doc.status === "ready").length;
  const isDocumentReady = selectedStatus === "ready";
  const canRunActions =
    selectedDocumentDetail !== null &&
    isDocumentReady &&
    !isActionLoading &&
    !isDetailLoading &&
    !isProcessing;

  return (
    <main className="container dashboard-container">
      <header className="dashboard-header">
        <div>
          <h1>Research workspace</h1>
          <p>Select a document, run a research action, review grounded output, and submit feedback.</p>
        </div>
        <Link href="/">Back to home</Link>
      </header>

      <section className="dashboard-summary workspace-summary">
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
          <p>Fetching workspace data from the API.</p>
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
          <p>Upload a document through the API to start this workspace flow.</p>
        </section>
      ) : null}

      {!isLoading && !errorMessage && documents.length > 0 ? (
        <>
          <DocumentList
            documents={documents}
            selectedDocumentId={selectedDocumentId}
            isProcessing={isProcessing}
            onSelect={setSelectedDocumentId}
          />

          <section className="workspace-panel">
            <div className="section-header-row">
              <h2>2. Document status and workspace</h2>
              <p>Process if needed, then run research actions.</p>
            </div>

            {selectedDocumentId === null ? (
              <section className="state-panel compact">
                <p className="state-title">No document selected</p>
                <p>Select a document above to continue.</p>
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
                <DocumentHeader
                  detail={selectedDocumentDetail}
                  isProcessing={isProcessing}
                  isDetailLoading={isDetailLoading}
                  processingStatusMessage={processingStatusMessage}
                  processingErrorMessage={processingErrorMessage}
                  onProcess={() => void handleProcessDocument()}
                  onRefreshDetail={() => void refreshSelectedDocumentDetail()}
                />
                <ResearchActionsPanel
                  canRunActions={canRunActions}
                  isActionLoading={isActionLoading}
                  isDetailLoading={isDetailLoading}
                  isProcessing={isProcessing}
                  isDocumentReady={isDocumentReady}
                  activeAction={activeAction}
                  questionInput={questionInput}
                  onActionChange={(action) => {
                    setActiveAction(action);
                    setActionErrorMessage(null);
                  }}
                  onQuestionChange={setQuestionInput}
                  onAskSubmit={(event) => void handleAskSubmit(event)}
                  onRunAction={() => void handleRunActionButton()}
                />
                <ResultPanel
                  isActionLoading={isActionLoading}
                  activeAction={activeAction}
                  actionErrorMessage={actionErrorMessage}
                  actionResult={actionResult}
                  streamingStatusMessage={streamingStatusMessage}
                />
                <AdvancedPanel
                  detail={selectedDocumentDetail}
                  isProcessing={isProcessing}
                  isDetailLoading={isDetailLoading}
                  documentChunks={documentChunks}
                  chunksCountFromApi={chunksCountFromApi}
                  isChunksLoading={isChunksLoading}
                  chunksErrorMessage={chunksErrorMessage}
                  isAdvancedOpen={isAdvancedOpen}
                  onToggle={handleAdvancedToggle}
                  onRefreshChunks={() => void refreshSelectedDocumentChunks()}
                />
                <FeedbackPanel
                  actionResult={actionResult}
                  feedbackValue={feedbackValue}
                  feedbackReason={feedbackReason}
                  feedbackReviewerNote={feedbackReviewerNote}
                  isSubmittingFeedback={isSubmittingFeedback}
                  feedbackSubmitErrorMessage={feedbackSubmitErrorMessage}
                  feedbackSubmitStatusMessage={feedbackSubmitStatusMessage}
                  feedbackRecords={feedbackRecords}
                  isFeedbackLoading={isFeedbackLoading}
                  feedbackLoadErrorMessage={feedbackLoadErrorMessage}
                  onValueChange={setFeedbackValue}
                  onReasonChange={setFeedbackReason}
                  onReviewerNoteChange={setFeedbackReviewerNote}
                  onSubmit={(event) => void handleSubmitFeedback(event)}
                  onRefreshFeedback={() => void refreshSelectedDocumentFeedback()}
                />
              </>
            ) : null}
          </section>
        </>
      ) : null}
    </main>
  );
}
