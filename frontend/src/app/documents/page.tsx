"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiClientError, listDocuments, type DocumentStatusModel } from "../../lib/api";

function formatCreatedAt(createdAt: string): string {
  const parsedDate = new Date(createdAt);
  if (Number.isNaN(parsedDate.getTime())) {
    return createdAt;
  }
  return parsedDate.toLocaleString();
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentStatusModel[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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
      if (error instanceof ApiClientError) {
        setErrorMessage(error.detail);
      } else if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("Unknown error while loading documents.");
      }
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadDocuments();
  }, []);

  const selectedDocument =
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
          <section className="selected-document-panel">
            {selectedDocument ? (
              <p>
                Selected document: #{selectedDocument.id} ({selectedDocument.company_name} -{" "}
                {selectedDocument.period})
              </p>
            ) : (
              <p>No document selected.</p>
            )}
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
                        disabled={document.id === selectedDocumentId}
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
