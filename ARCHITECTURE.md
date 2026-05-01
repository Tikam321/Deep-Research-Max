# Compliance Auditor Architecture

This document outlines the technical architecture of the Compliance Auditor, an AI-powered agent designed to cross-reference internal company policies against external regulatory standards using the Gemini Interactions API.

## System Overview

The system is built on a "Grounding-first" architecture. It treats external laws as the source of truth and internal documents as the audit targets.

### Core Technologies
- **Language**: Python 3.10+
- **SDK**: `google-genai` (v1.55.0+)
- **Models**:
  - **Audit Engine**: `deep-research-max-preview-04-2026` (Exhaustive analysis)
  - **Chat Engine**: `gemini-3.1-pro-preview` (Contextual follow-up)
- **Service**: Gemini Interactions API (Stateful & Asynchronous)

---

## Component Architecture

### 1. Ingestion Layer (Gemini File Service)
Users upload PDF documents through the application interface. The application does not store these files locally; instead, it proxies them to the **Gemini File Service**.
- **API Call**: `client.files.upload`
- **Purpose**: Provides high-capacity cloud storage (up to 2GB) where the model can "see" and "read" the documents.
- **Categorization**: Files are categorized as `external` (The Law) or `internal` (The Policy) to guide the agent's logic.

### 2. Analysis Layer (Deep Research Agent)
When an audit is triggered, the system orchestrates a long-running research task.
- **API Call**: `client.interactions.create(agent="deep-research-max-preview-04-2026", background=True)`
- **Tooling**: Uses the `file_search` tool to perform semantic retrieval across the uploaded URIs.
- **Processing**: Runs in the background to prevent connection timeouts during deep document analysis.
- **Output**: Produces a **Structured JSON Report** via `response_schema`, ensuring the findings (gaps, severity, remediation) are machine-readable.

### 3. Interaction Layer (Stateful Chat)
After the audit, the user can discuss the findings.
- **API Call**: `client.interactions.create(model="gemini-3.1-pro-preview")`
- **State Management**: Uses `previous_interaction_id` to maintain server-side memory. This allows the user to ask "How do I fix the third gap?" without re-uploading documents or re-running the full audit.

---

## Data Flow

1. **Upload**: User sends a PDF -> Backend calls Gemini File API -> Returns a `File URI`.
2. **Trigger**: User requests an audit -> Backend sends `File URIs` + `Instructions` to the Deep Research Max agent.
3. **Poll**: The backend polls the Interaction status every 15 seconds.
4. **Result**: Once `completed`, the JSON findings are displayed in the UI.
5. **Follow-up**: User asks a question -> Backend sends the query along with the `previous_interaction_id` to the model.

---

## Security & Privacy
- **No Training**: Documents uploaded to the Gemini File Service are not used for global model training.
- **Ephemeral Storage**: Files are stored temporarily (1-55 days depending on the tier) and can be manually deleted via `client.files.delete` once the audit is finalized.
- **Server-Side State**: Conversation history is stored securely on Google's infrastructure, reducing the risk of local data leaks in the client-side payload.

## Key API Endpoints Used
| Purpose | API Method |
| :--- | :--- |
| Document Hosting | `client.files.upload` |
| Gap Analysis | `client.interactions.create(agent="deep-research-max...")` |
| Task Monitoring | `client.interactions.get` |
| Contextual Chat | `client.interactions.create(model="gemini-3.1-pro...", previous_interaction_id=...)` |