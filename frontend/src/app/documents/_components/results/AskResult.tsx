import type { AskGroundedQuestionResponseModel } from "../../../../lib/api/models/documents";
import { CitationCards } from "../CitationCard";

interface AskResultProps {
  result: AskGroundedQuestionResponseModel;
}

export function AskResult({ result }: AskResultProps) {
  return (
    <>
      <div className="result-block">
        <p className="result-label">Question</p>
        <p className="result-text">{result.question}</p>
      </div>
      <div className="result-block">
        <p className="result-label">Answer</p>
        <p className="result-text">{result.answer}</p>
      </div>
      <div className="result-block">
        <p className="result-label">Citations</p>
        <CitationCards citations={result.citations} />
      </div>
    </>
  );
}
