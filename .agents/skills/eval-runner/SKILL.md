---
name: eval-runner
description: Validate prompt, retrieval, and answer quality changes using project eval cases. Use this for faithfulness, citation accuracy, and regression checks.
---

# When to use
Use this skill when a task changes prompts, retrieval logic, chunking, ranking, answer formatting, or verification logic.

# Workflow
1. Identify the exact behavior change.
2. Select the smallest relevant eval subset.
3. Run the eval command or test harness.
4. Report:
   - pass/fail
   - failure patterns
   - likely root cause
5. Suggest the smallest corrective change.

# Root-cause categories
- ingestion
- chunking
- metadata filtering
- retrieval ranking
- prompt design
- verification logic
- output formatting

# Reporting format
- Change under test
- Eval cases used
- Result summary
- Main failure mode
- Recommended fix