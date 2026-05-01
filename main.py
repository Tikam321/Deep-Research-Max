import asyncio
from google import genai
from typing import Optional, List, Dict, Union, BinaryIO

class Agent:
    """
    Compliance Auditor Agent using Gemini 3.1 and Deep Research.
    """
    def __init__(self, model: str = "gemini-3.1-pro-preview"):
        self.client = genai.Client()
        self.model = model
        self.research_agent = "deep-research-max-preview-04-2026"
        self.global_previous_interaction_id: Optional[str] = None
        # Separating storage for better prompting precision
        self.external_rules: List[Dict] = []
        self.internal_policies: List[Dict] = []

    def isInternalPolicyUploaded(self) -> bool:
        """Check if at least one internal policy has been uploaded."""
        return len(self.internal_policies) > 0
    
    def isExternalPolicyUploaded(self) -> bool:
        """Check if at least one external policy has been uploaded."""
        return len(self.external_rules) > 0

    def upload_document(self, file_input: Union[str, BinaryIO], display_name: str, category: str = "internal", mime_type: Optional[str] = None):
        """
        Uploads a document to the Gemini file service for grounding.
        category: 'external' for regulations, 'internal' for company policies.
        """
        print(f"  [System] Uploading {category.upper()} doc to Gemini File Service: {display_name}...")

        # Check if file already exists in our lists to avoid duplicate processing
        target_list = self.external_rules if category == "external" else self.internal_policies
        for existing_file in target_list:
            if existing_file["display_name"] == display_name:
                print(f"  [System] Document '{display_name}' already uploaded. Reusing existing URI.")
                # Return a mock file object with the existing URI
                return type('obj', (object,), {'uri': existing_file['uri']})
        
        config = {'display_name': display_name}
        if mime_type:
            config['mime_type'] = mime_type

        # The SDK requires keyword arguments for 'path' (string) or 'file' (BinaryIO)
        if isinstance(file_input, str):
            file = self.client.files.upload(path=file_input, config=config)
        else:
            file = self.client.files.upload(file=file_input, config=config)
        
        if category == "external":
            self.external_rules.append({"uri": file.uri, "name": file.name, "display_name": display_name})
        else:
            self.internal_policies.append({"uri": file.uri, "name": file.name, "display_name": display_name})
        return file

    def delete_all_uploaded_files(self):
        """
        Deletes all files uploaded to the Gemini File Service during this agent's session.
        """
        print("  [System] Deleting all uploaded files from Gemini File Service...")
        for file_info in self.external_rules + self.internal_policies:
            try:
                self.client.files.delete(file_info["name"])
                print(f"  [System] Deleted: {file_info['display_name']} ({file_info['name']})")
            except Exception as e:
                print(f"  [System] Error deleting {file_info['display_name']}: {e}")

    async def run_audit(self, audit_instruction: str):
        """
        Triggers a Deep Research task to find loopholes and compliance gaps.
        """
        if not self.external_rules or not self.internal_policies:
            return "Error: Please upload both external regulations and internal policies first."

        print(f"  [System] Starting Deep Research Audit...")
        
        # Build multimodal input parts for proper grounding. 
        # Gemini requires file_data parts to actually "see" the documents.
        full_input = [{"type": "text", "text": f"{audit_instruction}\n\nEXTERNAL REGULATIONS (Source of Truth):"}]
        for f in self.external_rules:
            full_input.append({"type": "text", "text": f"\nRegulation Document: {f['display_name']}"})
            full_input.append({"type": "document", "uri": f["uri"], "mime_type": "application/pdf"})
        
        full_input.append({"type": "text", "text": "\nINTERNAL COMPANY POLICIES (Documents to Audit):"})
        for f in self.internal_policies:
            full_input.append({"type": "text", "text": f"\nCompany Policy: {f['display_name']}"})
            full_input.append({"type": "document", "uri": f["uri"], "mime_type": "application/pdf"})
        
        full_input.append({"type": "text", "text": "\nPlease use the file_search tool to cross-reference these documents."})
        full_input.append({
            "type": "text",
            "text": (
                "\nProvide the final audit report in a strict JSON format. "
                "The JSON must have a 'findings' key containing an array of objects. "
                "Each object should include: 'requirement', 'status' (compliant, non-compliant, or partial), 'gap_description', and 'remediation_steps'."
                "\nAt the end of your comprehensive narrative report, you MUST provide a summary in a markdown JSON code block. "
                "The JSON block must follow this structure: "
                "```json\n"
                "{\"findings\": [{\"requirement\": \"string\", \"status\": \"compliant|non-compliant|partial\", \"gap_description\": \"string\", \"remediation_steps\": \"string\"}]}\n"
                "```"
            )
        })

        interaction = self.client.interactions.create(
            agent=self.research_agent,
            input=full_input,
            tools=[{"type": "file_search"}],  # Correct format for built-in file_search tool
            background=True,  # Passed directly
            previous_interaction_id=self.global_previous_interaction_id # Reuse state if this is a re-audit
        )

        # Poll for completion
        while True:
            interaction = self.client.interactions.get(interaction.id)
            if interaction.status == "completed":
                self.global_previous_interaction_id = interaction.id
                if interaction.outputs and interaction.outputs[-1].text:
                    return interaction.outputs[-1].text
                return "Audit completed but no text output was found."
            elif interaction.status in ["failed", "cancelled"]:
                return f"Audit failed with status: {interaction.status}"
            
            print("  [System] Researching... (checking external regs vs internal policies)")
            await asyncio.sleep(20)

    async def chat(self, user_input: str) -> str:
        """Standard interaction for follow-up questions about the audit."""
        interaction = self.client.interactions.create(
            model=self.model,
            input=user_input,
            previous_interaction_id=self.global_previous_interaction_id
        )
        self.global_previous_interaction_id = interaction.id
        return interaction.outputs[-1].text if interaction.outputs else "No response."

def main():
    agent = Agent()
    
    print("--- STEP 1: Uploading Compliance Documents ---")
    # Example Usage:
    # agent.upload_document("./docs/eu_ai_act.pdf", "EU AI Act", category="external")
    # agent.upload_document("./docs/company_dev_handbook.pdf", "Dev Handbook", category="internal")
    
    total_docs = len(agent.external_rules) + len(agent.internal_policies)
    print(f"  [System] {total_docs} files ready for analysis.")

    print("\n--- STEP 2: Running Gap Analysis ---")
    audit_query = (
        "Perform a comprehensive audit. Identify any loopholes in our Internal Policies "
        "that do not align with the Transparency requirements of the External Regulations."
    )
    
    # This starts the background process and polls until complete
    # report = agent.run_audit(audit_query)
    # print(f"\nFinal Audit Report:\n{report}")

    print("\n--- STEP 3: Interactive Remediation ---")
    # print(agent.chat("Write a 3-paragraph policy update to fix the 'non-compliant' transparency gap."))

if __name__ == "__main__":
    main()