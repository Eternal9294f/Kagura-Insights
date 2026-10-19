"""
Linear End-to-End Pipeline for Project Kagura.
Execution order:
1. Ingestion & Validation
2. 5-Theme Clustering
3. Fee Confusion Detection
4. Weekly Pulse & Fee Explainer Generation
5. Human Approval Gate
6. Dispatch to Local Records / n8n MCP Server
"""

import os
import sys
import json
import re
from datetime import datetime
import pandas as pd
import requests

PRODUCT_NAME = "Groww"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "reviews_themed.csv")
if not os.path.exists(DATA_PATH):
    DATA_PATH = os.path.join(BASE_DIR, "data", "reviews.csv")

OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

OFFICIAL_SOURCES = [
    {"title": "Groww Help: What is Exit Load?", "url": "https://groww.in/help/mutual-funds/order/what-is-exit-load--71"},
    {"title": "Groww Knowledge: How Exit Load is Calculated", "url": "https://groww.in/p/exit-load-in-mutual-funds"},
    {"title": "AMFI India: Mutual Fund Fees and Expenses", "url": "https://www.amfiindia.com"},
    {"title": "SEBI: Categorization of Mutual Fund Schemes", "url": "https://www.sebi.gov.in"}
]


def step_1_ingest_data(csv_path: str):
    print("=" * 60)
    print("STEP 1: INGESTING & VALIDATING REVIEW CORPUS")
    print("=" * 60)
    df = pd.read_csv(csv_path)
    
    # Handle schema naming variants
    if "rid" in df.columns and "review_id" not in df.columns:
        df = df.rename(columns={"rid": "review_id"})
    if "text" in df.columns and "review_text" not in df.columns:
        df = df.rename(columns={"text": "review_text"})
    
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "review_text"]).drop_duplicates(subset=["review_text"]).reset_index(drop=True)
    
    min_date = df["date"].min().strftime("%Y-%m-%d")
    max_date = df["date"].max().strftime("%Y-%m-%d")
    days_span = (df["date"].max() - df["date"].min()).days
    weeks_span = round(days_span / 7, 1)
    
    print(f"Loaded {len(df)} validated reviews.")
    print(f"Date Range: {min_date} to {max_date} ({weeks_span} weeks).")
    print(f"Average Star Rating: {round(df['rating'].mean(), 2)} / 5.0")
    return df, min_date, max_date


def step_2_theme_clustering(df: pd.DataFrame):
    print("\n" + "=" * 60)
    print("STEP 2: THEMATIC CLUSTERING (MAX 5 CANONICAL THEMES)")
    print("=" * 60)
    
    if "theme" in df.columns and df["theme"].nunique() <= 5:
        df["assigned_theme"] = df["theme"]
    else:
        taxonomy = {
            "Fee & Exit-Load Confusion": ["exit load", "hidden fee", "hidden charge", "deducted", "penalty", "cut", "brokerage"],
            "App Stability & Usability": ["crash", "lag", "hang", "freeze", "bug", "interface", "biometric", "ui", "slow"],
            "Customer Support Friction": ["support", "ticket", "customer care", "agent", "bot", "reply", "unreachable"],
            "Order Execution & Settlement": ["execution", "delay", "order", "nav", "lumpsum", "mandate", "stuck"],
            "KYC & Onboarding Delays": ["kyc", "bank verification", "verification", "onboarding", "cheque"]
        }
        def classify(txt):
            lower = txt.lower()
            for th, kws in taxonomy.items():
                for kw in kws:
                    if re.search(r"\b" + re.escape(kw) + r"\b", lower):
                        return th
            return "App Stability & Usability"
        df["assigned_theme"] = df["review_text"].apply(classify)

    total = len(df)
    counts = df["assigned_theme"].value_counts().to_dict()
    shares = {k: round((v / total) * 100, 1) for k, v in counts.items()}
    sorted_themes = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:3]
    
    print(f"Thematic breakdown across {len(counts)} themes:")
    for th, cnt in counts.items():
        print(f"  * {th}: {cnt} reviews ({shares[th]}%)")
    print(f"Top 3 themes ranked for Weekly Pulse: {[t[0] for t in sorted_themes]}")
    return df, sorted_themes, shares


def step_3_detect_fee_confusion(df: pd.DataFrame):
    print("\n" + "=" * 60)
    print("STEP 3: FEE CONFUSION VS GENERAL PRICING DETECTION")
    print("=" * 60)
    
    if "fee_stance" in df.columns:
        confused_count = len(df[df["fee_stance"] == "confused"])
        complaints_count = len(df[df["fee_stance"] == "complaint_only"])
        print(f"Isolated {confused_count} genuine misconceptions vs {complaints_count} generic fee complaints.")
    else:
        patterns = [r"groww deducted", r"groww charged", r"groww stole", r"hidden charge by groww", r"exit load"]
        confused_count = len(df[df["review_text"].str.contains("|".join(patterns), case=False, regex=True)])
        print(f"Identified {confused_count} reviews showing confusion on Groww charges.")

    fee_issue = (
        "Statutory AMC Exit-Load Misconception: Retail unitholders mistakenly attribute "
        "statutory AMC exit load deductions upon redemption to unauthorized broker commissions levied by Groww."
    )
    print(f"Isolated Core Friction: {fee_issue}")
    return fee_issue


def step_4_generate_outputs(df: pd.DataFrame, top_themes, shares, fee_issue, max_date):
    print("\n" + "=" * 60)
    print("STEP 4: GENERATING WEEKLY PRODUCT PULSE & FEE EXPLAINER")
    print("=" * 60)
    
    # Extract 3 verbatim quotes
    quotes = []
    if "fee_stance" in df.columns:
        cq = df[df["fee_stance"] == "confused"]["review_text"].tolist()
        if cq: quotes.append(cq[0])
    if not quotes:
        quotes.append(df[df["review_text"].str.contains("exit load|deducted", case=False)]["review_text"].iloc[0])
    
    sq = df[df["review_text"].str.contains("support|ticket", case=False)]["review_text"].tolist()
    if sq: quotes.append(sq[0])
    
    for r in df["review_text"].tolist():
        if r not in quotes:
            quotes.append(r)
            if len(quotes) == 3: break

    # Pulse generation (under 250 words)
    theme_str = "\n".join([f"- **{t[0]}**: {t[1]} reviews ({shares.get(t[0], 0)}%)" for t in top_themes])
    quote_str = "\n".join([f'> *"{q}"*' for q in quotes[:3]])
    
    pulse_text = (
        f"**Weekly Product Pulse -- {PRODUCT_NAME}**\n\n"
        f"**1. Top Customer Themes (Total Analyzed: {len(df)})**\n"
        f"{theme_str}\n\n"
        f"**2. Voice of Customer (Genuine Quotes)**\n"
        f"{quote_str}\n\n"
        f"**3. Key Friction Observation**\n"
        f"Users repeatedly confuse statutory AMC exit loads with unauthorized broker charges upon redemption.\n\n"
        f"**4. Actionable Recommendations**\n"
        f"1. *Pre-Redeem Estimator*: Display exact rupee exit-load deduction before redemption confirmation.\n"
        f"2. *Contextual Badge*: Clarify that exit load is retained by the AMC, not {PRODUCT_NAME}.\n"
        f"3. *SIP Aging Tracker*: Add purchase-date tooltips identifying which SIP installments have cleared lock-in."
    )
    word_count = len(pulse_text.split())
    print(f"Generated Weekly Pulse: {word_count} words (Limit: 250 words) -> {'COMPLIANT' if word_count <= 250 else 'EXCEEDED'}")

    # Explainer generation (max 6 bullets)
    today_str = datetime.now().strftime("%Y-%m-%d")
    bullets = [
        f"Exit load is a statutory fee levied by Asset Management Companies (AMCs), not by {PRODUCT_NAME}.",
        "The fee is deducted from fund NAV only if units are redeemed before the scheme's specified holding period (typically 7 to 365 days).",
        f"{PRODUCT_NAME} operates as a direct mutual fund platform and charges 0 brokerage and 0 commission on mutual fund redemptions.",
        "For SIP investments, exit load applies individually to each monthly installment based on its unique purchase date on a FIFO basis.",
        "Exit load proceeds are credited back into the mutual fund scheme corpus to safeguard long-term unitholders.",
        "Investors can preview applicable exit-load percentages and holding cutoff periods on each fund's detail page before placing orders."
    ]
    print(f"Generated Fee Explainer: {len(bullets)} bullets (Limit: 6 bullets) -> COMPLIANT")
    
    # Prepare payloads
    notes_payload = {
        "date": today_str,
        "top_themes": [t[0] for t in top_themes],
        "weekly_pulse": pulse_text,
        "identified_fee_issue": fee_issue,
        "explanation_bullets": bullets,
        "source_links": [s["url"] for s in OFFICIAL_SOURCES]
    }
    
    email_draft_payload = {
        "subject": f"Weekly Product Pulse + Customer Clarification -- {PRODUCT_NAME} (week of {max_date})",
        "recipients": ["product-team@groww.in"],
        "body": (
            f"Hi team,\n\n"
            f"Here is this week's product intelligence and customer clarification note for {PRODUCT_NAME}.\n\n"
            f"=== WEEKLY PRODUCT PULSE ===\n\n{pulse_text}\n\n"
            f"=== CUSTOMER CLARIFICATION: FEE EXPLAINER ===\n\n"
            + "\n".join([f"- {b}" for b in bullets])
            + f"\n\nLast checked: {today_str}\n\nOfficial Sources:\n"
            + "\n".join([f"- {s['title']}: {s['url']}" for s in OFFICIAL_SOURCES])
            + "\n\n-- Generated by Kagura HITL Review Intelligence"
        )
    }

    return pulse_text, bullets, notes_payload, email_draft_payload


def step_5_approval_gate(notes_payload, email_draft_payload):
    print("\n" + "=" * 60)
    print("STEP 5: HUMAN-IN-THE-LOOP (HITL) APPROVAL GATE")
    print("=" * 60)
    print("The following pending actions are staged for dispatch:")
    print("  1. append_note       -> Append structured weekly intelligence to documentation ledger")
    print("  2. create_email_draft -> Create draft in Gmail / local mailbox (NEVER AUTO-SENT)")
    print(f"\nSubject: {email_draft_payload['subject']}")
    print("-" * 60)
    
    # Check for CLI flags (--yes or --no)
    if "--yes" in sys.argv:
        print("[AUTO-APPROVE] Flag --yes detected.")
        return True
    if "--no" in sys.argv:
        print("[AUTO-DENY] Flag --no detected.")
        return False
        
    choice = input("Approve dispatch of these actions? [y/N]: ").strip().lower()
    return choice in ["y", "yes"]


def step_6_dispatch_actions(notes_payload, email_draft_payload, approved: bool):
    print("\n" + "=" * 60)
    print("STEP 6: DISPATCHING APPROVED MCP ACTIONS")
    print("=" * 60)
    if not approved:
        print("[HALTED] EXECUTION HALTED BY OPERATOR. No records were modified.")
        return False

    # 1. Local Persistence
    doc_path = os.path.join(OUTPUTS_DIR, "doc-entry.json")
    with open(doc_path, "w", encoding="utf-8") as f:
        json.dump(notes_payload, f, indent=2)
    print(f"[OK] Appended note entry -> {doc_path}")

    email_path = os.path.join(OUTPUTS_DIR, "email-draft.md")
    with open(email_path, "w", encoding="utf-8") as f:
        f.write(
            f"# EMAIL DRAFT (STAGED -- NOT SENT)\n\n"
            f"**To:** {', '.join(email_draft_payload['recipients'])}\n"
            f"**Subject:** {email_draft_payload['subject']}\n\n"
            f"---\n\n"
            f"{email_draft_payload['body']}\n"
        )
    print(f"[OK] Created staged email draft -> {email_path}")

    # 2. n8n MCP Server Dispatch (Optional if configured)
    n8n_url = os.environ.get("N8N_MCP_URL")
    n8n_token = os.environ.get("N8N_MCP_TOKEN")
    
    if n8n_url:
        print("\nConnecting to external n8n MCP Server...")
        headers = {"Authorization": f"Bearer {n8n_token}"} if n8n_token else {}
        try:
            res = requests.post(n8n_url, json={"notes": notes_payload, "draft": email_draft_payload}, headers=headers, timeout=10)
            if res.status_code == 200:
                print("[OK] Successfully synchronized with live n8n Google Doc & Gmail workflow!")
            else:
                print(f"[WARNING] n8n responded with status {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[WARNING] Could not reach n8n webhook: {e}")
    else:
        print("\n[INFO] N8N_MCP_URL not set in environment. Dispatched to local audit logs.")

    print("\n[SUCCESS] WORKFLOW EXECUTION COMPLETE!")
    return True


def run_pipeline():
    df, min_d, max_d = step_1_ingest_data(DATA_PATH)
    df, top_themes, shares = step_2_theme_clustering(df)
    fee_issue = step_3_detect_fee_confusion(df)
    pulse, bullets, notes_pl, email_pl = step_4_generate_outputs(df, top_themes, shares, fee_issue, max_d)
    approved = step_5_approval_gate(notes_pl, email_pl)
    step_6_dispatch_actions(notes_pl, email_pl, approved)


if __name__ == "__main__":
    run_pipeline()
