# Compliance Auditor Agent

An AI-powered system designed to cross-reference internal company policies against external regulatory standards using the Gemini Interactions API and Deep Research.

## 🚀 Features & Implementation

- **Automated Gap Analysis**: Leverages the `deep-research-max-preview-04-2026` agent for exhaustive, background-processed audits.
- **FastAPI Integration**: A production-ready API for document ingestion, audit orchestration, and stateful chat.
- **Multimodal Search**: Interleaves text instructions with PDF `document` parts, allowing the `file_search` tool to perform high-precision grounding.
- **Cleanup Utilities**: Built-in methods to purge ephemeral data from the Gemini File Service.

## 🏗️ Architecture & Token Optimization

### Efficient History Tracking via Interaction ID
One of the core architectural advantages of this project is the use of **Server-Side State Management**.

- **How it works**: Instead of re-sending the entire conversation history or re-processing document chunks for every follow-up question, we track the `previous_interaction_id`.
- **Token Savings**: By referencing the interaction ID, the Gemini Interactions API reuses the context stored on the server. This avoids consuming tokens for redundant history transfers and eliminates the need for the model to "re-search" previous history to understand the current context.
- **Performance**: This leads to faster response times and significantly lower operational costs for long-running compliance dialogues.

### Deep Research & Grounding
- **Exhaustive Research**: We utilize the `deep-research-max` agent, which is specifically optimized for maximum comprehensiveness. It doesn't just look at the top results; it performs deep reasoning to find subtle loopholes.
- **Multimodal Interleaving**: Our input structure explicitly separates "External Regulations (Source of Truth)" from "Internal Company Policies (Audit Targets)" by interleaving text labels with `document` URIs. This ensures the model knows exactly which document represents the requirement and which is being audited.

## 🛠️ Getting Started

### Prerequisites
- Python 3.10+
- Gemini API Key (stored in `.env`)

### Installation
```bash
pip install -r requirements.txt
```

### Running the Server
```bash
uvicorn api:app --reload
```

## 📡 API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/upload-docs` | POST | Uploads PDFs to Gemini File Service (internal or external). |
| `/run-audit` | POST | Triggers a background Deep Research audit task. |
| `/chat` | POST | Follow-up conversation using server-side context (`interaction_id`). |
| `/cleanup` | POST | Deletes all files from the Gemini File Service session. |
| `/internal-policies` | GET | Checks if internal documents are ready. |

## 📄 Technical Details

- **Model**: `gemini-3.1-pro-preview`
- **Agent**: `deep-research-max-preview-04-2026`
- **SDK**: `google-genai >= 1.55.0`

## 🛡️ Privacy
Documents are uploaded to the Gemini File Service and are not used for global model training. Files are ephemeral and can be deleted programmatically.