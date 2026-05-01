import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from typing import List
from main import Agent # Assuming main.py is in the same directory

app = FastAPI(
    title="Compliance Auditor API",
    description="API for uploading documents, running compliance audits, and interacting with the agent.",
    version="1.0.0",
)

# Initialize the Agent instance globally
agent = Agent()

@app.get("/internal-policies", summary="Check if internal policies are uploaded")
async def check_internal_policies():
    return {"is_uploaded": agent.isInternalPolicyUploaded()}

@app.get("/external-policies", summary="Check if external policies are uploaded")
async def check_external_policies():
    return {"is_uploaded": agent.isExternalPolicyUploaded()}

@app.post("/upload-docs", summary="Upload documents for audit")
async def upload_docs(
    category: str = Form(..., description="Category of the document: 'external' for regulations, 'internal' for company policies."),
    file: UploadFile = File(..., description="The PDF file to upload.")
):
    """
    API Endpoint for users to upload documents.
    It proxies the file stream directly to Gemini's cloud storage.
    """
    if category not in ["external", "internal"]:
        raise HTTPException(status_code=400, detail="Category must be 'external' or 'internal'.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail=f"Only PDF files are allowed. Received: {file.filename}")
    
    try:
        # Pass the file stream directly to the Agent
        gemini_file_info = agent.upload_document(file.file, file.filename, category=category, mime_type=file.content_type)
        return {
            "status": "success",
            "uploaded_file": {
                "filename": file.filename,
                "uri": gemini_file_info.uri,
                "category": category
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload {file.filename}: {str(e)}")

@app.post("/run-audit", summary="Trigger a compliance audit")
async def start_audit(
    instruction: str = Form(..., description="Specific instructions for the audit, e.g., 'Identify transparency gaps'.")
):
    """
    Trigger the Deep Research audit based on previously uploaded files.
    This will block until the audit is complete (can take several minutes).
    """
    report = await agent.run_audit(audit_instruction=instruction)
    try:
        # Try to find the JSON block first
        if "```" in report:
            parts = report.split("```")
            for part in reversed(parts):
                if "findings" in part.lower():
                    json_str = part.replace("json", "", 1).strip()
                    return json.loads(json_str)
        
        # Fallback to direct load if no markdown blocks are found
        return json.loads(report)
    except json.JSONDecodeError:
        # If parsing fails, return the report as a narrative result instead of an 'error'
        return {"status": "success", "type": "narrative", "content": report}

@app.post("/chat", summary="Engage in follow-up conversation")
async def follow_up(
    message: str = Form(..., description="Your follow-up question or statement.")
):
    """
    Standard chat for follow-up questions, maintaining context from the audit.
    """
    response = await agent.chat(message)
    return {"response": response}

@app.post("/cleanup", summary="Delete all uploaded files from Gemini File Service")
async def cleanup_files():
    """
    Deletes all files that were uploaded to the Gemini File Service during this session.
    """
    agent.delete_all_uploaded_files()
    return {"status": "success", "message": "All uploaded files have been deleted from Gemini File Service."}