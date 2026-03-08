---
name: rag-debugger
description: Diagnose groundedness, bad citations, weak retrieval, or missed evidence in a RAG workflow.
---

# When to use
Use this skill when the final answer is ungrounded, cites the wrong evidence, misses obvious evidence, or answers with high confidence despite weak support.

# Workflow
1. Inspect the user query.
2. Inspect retrieved chunks and metadata filters.
3. Compare retrieved evidence with the final answer.
4. Identify the failure source:
   - ingestion
   - chunking
   - metadata
   - ranking
   - prompt
   - post-processing
5. Recommend the smallest fix first.

# Debug questions
- Was the right document retrieved at all?
- Was the relevant chunk split incorrectly?
- Did metadata filters exclude the correct source?
- Did the model ignore retrieved evidence?
- Did the answer over-generalize beyond the sources?

# Output format
- Symptom
- Most likely cause
- Evidence for diagnosis
- Smallest viable fix
- Follow-up eval to run