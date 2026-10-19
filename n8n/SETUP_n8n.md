# n8n Setup Guide — Kagura MCP Server (5–10 Minutes)

Follow these 4 simple steps to connect your n8n automation with Project Kagura. **No coding required.**

---

## 📌 Prerequisites
- A running n8n instance (Cloud or Local: `npx n8n`).
- A Google account (for Google Docs and Gmail draft creation).

---

## Part 1 — Import the Workflow (1 min)

1. Open n8n in your browser.
2. Go to **Workflows** → click **Add Workflow** (or the **+** button).
3. Click the **three dots (⋯)** in the top right corner → select **Import from File**.
4. Choose the file:
   `groww-insights/kagura-insights/n8n/kagura-mcp-workflow.json`
5. You will see 4 connected blocks:
   - **MCP Server Trigger** (left webhook listener)
   - **append_to_doc** (Google Docs node)
   - **read_doc** (Google Docs node)
   - **create_email_draft** (Gmail draft creator)

---

## Part 2 — Configure Bearer Authentication (2 min)

1. Double-click the **MCP Server Trigger** node.
2. Under **Authentication**, select **Header Auth** or **Bearer Auth**.
3. Click **Create New Credential** and enter a secret token (e.g. `kagura_secret_token_2026`).
4. Save the credential.
5. Note your **Production URL** (displayed at the bottom of the node after activating).

---

## Part 3 — Connect Google Doc & Gmail (5 min)

1. Go to [docs.google.com](https://docs.google.com) → create a blank document called **Weekly Product Pulse — Groww**.
2. Copy the **Document ID** from your browser address bar:
   `https://docs.google.com/document/d/`**`1a2B3c4D5e...`**`/edit`
3. In n8n, open the **append_to_doc** node:
   - Connect your **Google Docs OAuth2** account.
   - Paste your **Document ID** into the `Document ID or URL` field.
4. Open the **read_doc** node and paste the same **Document ID**.
5. Open the **create_email_draft** node:
   - Connect your **Gmail OAuth2** account.
   - Leave the rest untouched (it only generates drafts, never sends).

---

## Part 4 — Activate Workflow & Test

1. Toggle the workflow to **Active** (switch at top right of n8n).
2. Copy the **Production URL** from the MCP Server Trigger.
3. In your project, set:
   ```env
   N8N_MCP_URL="https://your-n8n-instance.com/webhook/kagura-pulse"
   N8N_MCP_TOKEN="kagura_secret_token_2026"
   GOOGLE_DOC_ID="your_google_doc_id"
   ```
4. Run `python workflow.py` to trigger the linear pipeline!

---

## 🛡️ Built-in Safety & Security Guardrails
- **No Email Sending**: Uses Gmail's `create draft` action exclusively. There is no `send` capability by design.
- **Single Doc Isolation**: The tool can only write to the explicit document ID you configured.
- **Bearer Token Security**: Rejects unauthorized access attempts.
- **Human Approval**: The linear workflow asks for explicit human consent before any payload is dispatched.
