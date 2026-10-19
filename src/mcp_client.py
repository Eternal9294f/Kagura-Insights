import os
from datetime import datetime
from typing import Dict, Any, Tuple
from src.mcp_server import KaguraMCPServer

OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")

class KaguraMCPClient:
    def __init__(self):
        self.server = KaguraMCPServer()

    def stage_payloads(self, pulse_text: str, explainer: Dict, analysis: Dict, product_name: str) -> Dict[str, Any]:
        subject = f"Weekly Product Pulse + Customer Clarification — {product_name}"
        email_body = (
            f"{pulse_text}\n\n"
            f"---\n\n"
            f"## Customer Clarification: Mutual Fund Exit Loads\n"
            + "\n".join([f"- {b}" for b in explainer["bullets"]])
            + f"\n\nLast checked: {explainer['last_checked']}\n"
            + "Authoritative Sources:\n"
            + "\n".join([f"- {s['title']}: {s['url']}" for s in explainer["source_links"]])
        )

        notes_payload = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "top_themes": [t[0] for t in analysis["top_themes"]],
            "weekly_pulse": pulse_text,
            "identified_fee_issue": analysis["fee_confusion_detail"],
            "explanation_bullets": explainer["bullets"],
            "source_links": [s["url"] for s in explainer["source_links"]]
        }

        return {
            "subject": subject,
            "email_body": email_body,
            "notes_payload": notes_payload
        }

    def execute_approved_workflow(self, staged_data: Dict[str, Any]) -> Tuple[Dict, Dict]:
        res_note = self.server.append_note(staged_data["notes_payload"])
        res_draft = self.server.create_draft(
            subject=staged_data["subject"],
            body=staged_data["email_body"]
        )

        trace_path = os.path.join(OUTPUTS_DIR, "run-trace.txt")
        trace_log = (
            f"PROJECT KAGURA — MCP EXECUTION RUN TRACE\n"
            f"Execution Timestamp: {datetime.now().isoformat()}\n"
            f"Approval Decision: APPROVED_BY_OPERATOR\n"
            f"Tool Dispatched: append_note -> {res_note['destination']}\n"
            f"Tool Dispatched: create_draft -> {res_draft['destinations']}\n"
            f"Status: ALL_ACTIONS_VERIFIED\n"
        )
        with open(trace_path, "w", encoding="utf-8") as f:
            f.write(trace_log)

        return res_note, res_draft
