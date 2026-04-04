import type { DocumentStatusModel } from "../../../lib/api/models/documents";
import { formatCreatedAt, getStatusTone } from "./shared";

interface DocumentListProps {
  documents: DocumentStatusModel[];
  selectedDocumentId: number | null;
  isProcessing: boolean;
  onSelect: (id: number) => void;
}

export function DocumentList({ documents, selectedDocumentId, isProcessing, onSelect }: DocumentListProps) {
  return (
    <section className="documents-table-section">
      <div className="section-header-row">
        <h2>1. Select document</h2>
        <p>Choose one document to enter the workspace.</p>
      </div>

      <section className="documents-table-wrapper">
        <table className="documents-table">
          <thead>
            <tr>
              <th>select</th>
              <th>id</th>
              <th>company</th>
              <th>type</th>
              <th>period</th>
              <th>status</th>
              <th>created</th>
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
                    onClick={() => onSelect(document.id)}
                    disabled={document.id === selectedDocumentId || isProcessing}
                  >
                    {document.id === selectedDocumentId ? "Selected" : "Select"}
                  </button>
                </td>
                <td>{document.id}</td>
                <td>{document.company_name}</td>
                <td>{document.document_type}</td>
                <td>{document.period}</td>
                <td>
                  <span className={`status-pill ${getStatusTone(document.status)}`}>
                    {document.status}
                  </span>
                </td>
                <td title={document.created_at}>{formatCreatedAt(document.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </section>
  );
}
