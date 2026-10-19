# 🔥 Project Kagura: Review Intelligence & MCP Workflow

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
[![NextLeap Fellowship](https://img.shields.io/badge/NextLeap-Milestone%204-purple.svg)](https://nextleap.app)
[![Tests Passing](https://img.shields.io/badge/pytest-7%20passed-brightgreen.svg)]()

**Project Kagura** transforms customer reviews into a structured **Weekly Product Pulse** and regulatory customer clarifications for **Groww**, gated by a strict **Human-in-the-Loop (HITL) Model Context Protocol (MCP)** execution layer.

---

## 📌 Executive Summary & Problem Space

- **Target Entity**: Groww (NextBillion Technology Pvt. Ltd.)
- **Primary Product Analyzed**: Groww Mutual Funds & Direct Investing App
- **Primary Friction Isolated**: **Statutory AMC Exit-Load Misconception**
  - Retail investors redeeming mutual fund units within the statutory exit window observe a 0.5%–1.0% deduction from their redemption proceeds.
  - Users misattribute this statutory AMC fee to unauthorized broker cuts or hidden commissions levied by Groww.
  - This drives customer support tickets, negative 1-star reviews, and unitholder churn.

---

## 🏗️ Architecture & Pipeline

```
  [ Reviews CSV (Google Play / App Store / X) ]
                       │
                       ▼
        [ Ingestion & Date Window Filter ] (8-12 weeks)
                       │
                       ▼
        [ Theme Clustering & Frequency Engine ] (Strictly ≤ 5 Themes)
                       │
                       ▼
        [ Fee Confusion Co-occurrence Detector ]
                       │
                       ▼
        [ Generation Layer (Deterministic, Zero-Cost) ]
         ├─ Weekly Product Pulse (≤ 250 words)
         └─ Customer Fee Explainer (≤ 6 bullets + official links)
                       │
                       ▼
        [ HUMAN-IN-THE-LOOP APPROVAL GATE ] ──(DENIED)──► Abort & log trace
                       │
                  (APPROVED)
                       │
                       ▼
        [ MCP Client -> MCP Server Tools ]
         ├─ append_note       ──► outputs/doc-entry.json
         └─ create_draft      ──► outputs/email-draft.md & .eml (NEVER AUTO-SENT)
```

---

## 📋 Requirement Compliance Matrix

| Requirement | Implementation | Compliance Proof |
| :--- | :--- | :--- |
| **Review Corpus (8-12 weeks)** | `data/reviews.csv` spans 2026-08-10 to 2026-10-08 | `test_csv_validation_and_windowing` PASSED |
| **Theme Cap (≤ 5 Themes)** | Canonical 5-category taxonomy | `test_theme_cap_and_percentages` PASSED |
| **Top 3 Themes Identified** | Ranked by volume and percentage share | Tab 1 & Pulse Section 1 |
| **3 Verbatim Quotes** | Extracted verbatim from corpus slices | `test_verbatim_quote_grounding` PASSED |
| **Isolated Fee Confusion** | Pinpoints Exit Load misattribution | `test_fee_confusion_vs_complaint` PASSED |
| **Weekly Pulse (≤ 250 words)** | Formatted note with 3 actionable recommendations | `test_weekly_pulse_word_count_and_recommendations` PASSED |
| **Fee Explainer (≤ 6 bullets)** | 6 factual bullets + 2 verified official links | `test_fee_explainer_bullet_and_link_rules` PASSED |
| **Approval-Gated MCP** | Human must click Approve; Deny aborts actions | `test_mcp_workflow_and_payload_schemas` PASSED |
| **Draft Protection** | Saves `.md` and `.eml` drafts; **zero auto-send** | Staged email draft verification |

---

## 🚀 Quickstart Guide (Local Run)

### 1. Prerequisites
- Python 3.10+ installed

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Automated Tests
```bash
python -m pytest tests/test_kagura.py -v
```
*(All 7 tests pass in < 1 second)*

### 4. Launch Interactive Streamlit App
```bash
streamlit run streamlit_app.py
```
Open your browser at `http://localhost:8501`.

---

## 🔒 MCP Safety & Guardrails
1. **Approval Required**: No file mutation or note appending occurs before the operator clicks **"✅ Approve & Dispatch MCP Tools"**.
2. **Deny Behavior**: Clicking **"❌ Deny"** immediately aborts dispatch; output files remain untouched.
3. **No Auto-Send**: The email draft tool only generates local `.md` and `.eml` files. It has no SMTP or outbound API credentials.

---

## 📚 Official Source Registry
1. **Groww Help Center**: [What is Exit Load?](https://groww.in/help/mutual-funds/order/what-is-exit-load--71)
2. **Groww Digest**: [How Exit Load is Calculated](https://groww.in/p/exit-load-in-mutual-funds)
3. **AMFI India**: [Mutual Fund Fees and Expenses](https://www.amfiindia.com)
4. **SEBI Circulars**: [Categorization and Rationalization of Mutual Fund Schemes](https://www.sebi.gov.in)

---

## 👤 Attribution & License
- Originally derived from and inspired by [kavitamotiwal/groww-insights](https://github.com/kavitamotiwal/groww-insights).
- Refactored, enhanced, and personalized for **NextLeap Product Management Fellowship Milestone 4** by Student Candidate.
- Licensed under MIT.
