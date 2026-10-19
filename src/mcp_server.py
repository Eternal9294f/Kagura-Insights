import os
import json
from datetime import datetime
from typing import Dict, Any

OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")

def ensure_output_dir():
    os.makedirs(OUTPUTS_DIR, exist_ok=True)

class KaguraMCPServer:
    @staticmethod
    def append_note(payload: Dict[str, Any]) -> Dict[str, Any]:
        ensure_output_dir()
        required = [
            "date", "top_themes", "weekly_pulse", "identified_fee_issue",
            "explanation_bullets", "source_links"
        ]
        for key in required:
            if key not in payload:
                raise ValueError(f"MCP Schema Violation: Missing mandatory field '{key}'")

        log_path = os.path.join(OUTPUTS_DIR, "doc-entry.json")
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return {
            "status": "success",
            "tool": "append_note",
            "destination": log_path,
            "timestamp": datetime.now().isoformat()
        }

    @staticmethod
    def create_draft(subject: str, body: str, recipients: str = "product-team@groww.in") -> Dict[str, Any]:
        ensure_output_dir()
        md_path = os.path.join(OUTPUTS_DIR, "email-draft.md")
        eml_path = os.path.join(OUTPUTS_DIR, "email-draft.eml")

        md_content = (
            f"# EMAIL DRAFT (STAGED - DO NOT AUTO-SEND)\n\n"
            f"**To:** {recipients}\n"
            f"**Subject:** {subject}\n"
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"---\n\n"
            f"{body}\n"
        )
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        eml_content = (
            f"To: {recipients}\n"
            f"Subject: {subject}\n"
            f"Date: {datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0530')}\n"
            f"Content-Type: text/plain; charset=utf-8\n"
            f"X-Unsent: 1\n\n"
            f"{body}"
        )
        with open(eml_path, "w", encoding="utf-8") as f:
            f.write(eml_content)

        return {
            "status": "success",
            "tool": "create_draft",
            "destinations": [md_path, eml_path],
            "subject": subject,
            "recipients": recipients,
            "timestamp": datetime.now().isoformat()
        }
