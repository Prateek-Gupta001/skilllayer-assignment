# SPEC — Personal Brain (skiLLLayer SDE I Take-Home)

Status: written before implementation. All commits should be traceable back
to a section below.

## 1. Problem statement

Build a conversational agent that answers natural-language questions by
pulling facts from at least two connected personal tools and reasoning
across them in a single answer, via a CLI query interface.

## 2. Scope

**Connectors (2):** Gmail, Google Drive.

**Interface:** CLI (Go binary), chat-style prompt loop — not curl commands.



## 3. Non-goals (explicit, to keep scope bounded)

- No Notion or Slack connector — two sources (Gmail, Drive) is sufficient
  per the assignment's minimum bar.
- No production-grade incremental sync — collectors pull a bounded recent
  window (last ~50 items per source) on manual invocation, not continuous
  sync. A real version would need incremental/delta sync.
- No binary text extraction (PDF parsing, OCR) for Drive files — Google-native
  docs and plain text files get full content extraction; other file types
  are recorded as metadata-only (filename, mimeType, timestamps). This is a
  stated limitation, not a bug: full binary parsing is orthogonal to proving
  cross-source retrieval works.
- No ingestion-time LLM classification (status tagging, entity extraction
  per email). Hybrid retrieval + the final synthesis call reasoning over raw
  retrieved content replaces this — see Section 5.
- No hosted embedding API — local embeddings only (see Section 6), since no
  embedding API key is available/needed for this scope.
- No custom vector index or reranker implementation — retrieval quality is
  entirely delegated to gbrain's built-in hybrid search.

## 4. Architecture

```
Python collectors (Gmail API, Drive API)
        │  write native-field frontmatter .md files, no LLM calls
        ▼
gbrain repo (local, git-backed)
        │  gbrain sync → ingest
        │  gbrain embed --all → local embeddings via Ollama
        ▼
gbrain hybrid retrieval (vector + BM25 + RRF, local embedding model)
        ▲
        │  gbrain query "<text>" --filter source=gmail|drive  (via subprocess)
        │
Go CLI orchestrator (Gemini function-calling loop)
   ├─ search_gmail_facts(query: string)  → GmailAgent → gbrain query --filter source=gmail
   └─ search_drive_facts(query: string)  → DriveAgent → gbrain query --filter source=drive
        │
        ▼
Final Gemini synthesis call: retrieved facts (both sources) → conversational answer
        │
        ▼
Printed to CLI
```

Cross-source reasoning happens at two points, by design: (1) implicitly,
because both sources are ingested into the same gbrain corpus so shared
entities (company names, thread references) surface together under a single
semantic query; and (2) explicitly, in the final synthesis call, where the
model is handed facts from both tool calls and asked to reconcile them into
one answer.

## 5. Data model

Frontmatter fields are **native API fields only** — no LLM-derived fields at
ingestion time. Status/classification reasoning is deferred to query-time,
where the synthesis LLM reads actual retrieved email/file content rather
than trusting a pre-baked tag that could be stale or wrong.

**Gmail** (`~/skilllayer-brain/gmail/<message_id>.md`):
```yaml
---
source: gmail
message_id: <id>
thread_id: <id>
from: <sender>
to: <recipient>
subject: <subject>
date: <date>
labels: [<gmail label ids>]
---
<plain-text body, or stripped HTML, or snippet as fallback>
```

**Drive** (`~/skilllayer-brain/drive/<file_id>.md`):
```yaml
---
source: drive
file_id: <id>
filename: <name>
mime_type: <mimeType>
modified_time: <modifiedTime>
owner: <owner email>
web_view_link: <link>
size_bytes: <size>
---
<extracted text for Google Docs / plain text files, else a note that
content was not extracted for this scope>
```

## 6. Retrieval

gbrain, standalone (non-agent) install:
- Storage: local PGLite, git-backed repo for idempotent `gbrain sync`
- Embeddings: local via Ollama, `nomic-embed-text` (768 dimensions) — no
  hosted embedding API key required
- Retrieval mode: hybrid (vector + BM25 with Reciprocal Rank Fusion),
  gbrain's default — no custom retrieval logic implemented by this project
- Query interface: `gbrain query "<natural language>"`, optionally scoped
  with `--filter source=gmail|drive`, invoked from Go via subprocess and
  stdout parsed

## 7. Tool definitions (subagents)

Two tools exposed to the orchestrating Gemini call, each taking a single
free-text argument — the model itself is responsible for writing an
intent-rich standalone query per tool call, not just echoing the user's raw
question:

```
search_gmail_facts(query: string)
  "An intent-rich natural language query to search the user's Gmail history."

search_drive_facts(query: string)
  "An intent-rich natural language query to search the user's Drive files."
```

Each tool's implementation (`GmailAgent`, `DriveAgent`) is a thin wrapper:
take the query string, call `gbrain query <query> ` and using hybrid RAG get the most retrieval text chunks.

## 8. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Collectors | Python (`google-api-python-client`) | Mature, low-friction OAuth + Gmail/Drive SDKs |
| Storage + retrieval | gbrain (standalone), PGLite, local Ollama embeddings | Satisfies assignment's storage requirement; hybrid search out of the box |
| Orchestrator / CLI | Go, Gemini Go SDK (function calling) | Matches candidate's target stack; clean tool-calling loop |
| LLM | Gemini (free tier API key) | No cost, adequate function-calling support |


