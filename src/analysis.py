import re
from datetime import datetime
from typing import Dict, List, Tuple
import pandas as pd

THEME_TAXONOMY = {
    "Fee & Exit-Load Confusion": [
        "exit load", "hidden fee", "hidden charge", "deducted", "unauthorized deduction",
        "stole", "penalty", "cut", "brokerage", "charges", "charges applicable", "proceeds",
        "service charges", "contract note", "hidden charges"
    ],
    "App Stability & Usability": [
        "crash", "lag", "hang", "freezes", "bug", "interface", "biometric", "dark mode", "ui", "login", "slow"
    ],
    "Customer Support Friction": [
        "support", "ticket", "customer care", "agent", "bot", "reply", "unreachable", "disconnected", "call"
    ],
    "Order Execution & Settlement": [
        "execution", "delay", "order", "nav", "lumpsum", "mandate", "stuck", "processing", "trading", "square off"
    ],
    "KYC & Onboarding Delays": [
        "kyc", "bank verification", "verification", "onboarding", "cheque", "re-kyc"
    ]
}

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Supports both standard schema (review_id, review_text) and review-pulse schema (rid, text)."""
    rename_map = {}
    if "rid" in df.columns and "review_id" not in df.columns:
        rename_map["rid"] = "review_id"
    if "text" in df.columns and "review_text" not in df.columns:
        rename_map["text"] = "review_text"
    if "source" not in df.columns:
        df["source"] = "Google Play / App Store"
    
    if rename_map:
        df = df.rename(columns=rename_map)
    return df

def validate_and_load_reviews(csv_file_or_path) -> Tuple[pd.DataFrame, str]:
    try:
        df = pd.read_csv(csv_file_or_path)
    except Exception as e:
        return pd.DataFrame(), f"Failed to parse CSV: {str(e)}"

    df = normalize_columns(df)

    required = ["review_id", "date", "rating", "review_text"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return pd.DataFrame(), f"Malformed schema: Missing mandatory columns {missing}"

    df["review_text"] = df["review_text"].fillna("").astype(str)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    
    initial_count = len(df)
    df = df.dropna(subset=["date"])
    df = df[df["review_text"].str.strip() != ""]
    df = df.drop_duplicates(subset=["review_text"]).reset_index(drop=True)
    clean_count = len(df)
    
    msg = f"Validated {clean_count} clean records ({initial_count - clean_count} excluded)."
    return df, msg

def filter_by_weeks(df: pd.DataFrame, weeks: int = 12) -> pd.DataFrame:
    if df.empty:
        return df
    max_d = df["date"].max()
    min_d = max_d - pd.Timedelta(weeks=weeks)
    return df[df["date"] >= min_d].copy().reset_index(drop=True)

def classify_primary_theme(text: str) -> str:
    lower = text.lower()
    for theme, keywords in THEME_TAXONOMY.items():
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", lower):
                return theme
    return "App Stability & Usability"

def analyze_corpus(df: pd.DataFrame) -> Dict:
    if df.empty:
        return {
            "total_reviews": 0, "theme_counts": {}, "theme_percentages": {},
            "top_themes": [], "verbatim_quotes": [], "fee_confusion_detected": False,
            "fee_confusion_detail": "No review corpus loaded."
        }

    # If the dataset already has a precomputed high-quality theme column, respect it if mapped to <= 5 categories
    if "theme" in df.columns and df["theme"].nunique() <= 5:
        df["assigned_theme"] = df["theme"]
    else:
        df["assigned_theme"] = df["review_text"].apply(classify_primary_theme)

    total = len(df)
    counts = df["assigned_theme"].value_counts().to_dict()
    percentages = {k: round((v / total) * 100, 1) for k, v in counts.items()}

    sorted_themes = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    top_3 = sorted_themes[:3]

    quotes = []
    # If fee_stance exists and has 'confused', prioritize that for the fee quote!
    if "fee_stance" in df.columns:
        confused_rows = df[df["fee_stance"] == "confused"]["review_text"].tolist()
        if confused_rows:
            quotes.append(confused_rows[0])
            
    fee_reviews = df[df["assigned_theme"] == "Fee & Exit-Load Confusion"]["review_text"].tolist()
    if not quotes and fee_reviews:
        quotes.append(fee_reviews[0])
    
    supp_reviews = df[df["assigned_theme"].astype(str).str.contains("Support", case=False)]["review_text"].tolist()
    if supp_reviews and supp_reviews[0] not in quotes:
        quotes.append(supp_reviews[0])
        
    other_reviews = df[~df["review_text"].isin(quotes)]["review_text"].tolist()
    if other_reviews:
        quotes.append(other_reviews[0])

    while len(quotes) < 3 and len(df) >= 3:
        for r in df["review_text"].tolist():
            if r not in quotes:
                quotes.append(r)
                if len(quotes) == 3:
                    break

    misconception_patterns = [
        r"groww deducted", r"groww charged", r"groww stole", r"hidden charge by groww",
        r"unauthorized deduction", r"secretly charging", r"exit load", r"deduct money from account without any reason"
    ]
    misconceptions = df[df["review_text"].str.contains("|".join(misconception_patterns), case=False, regex=True)]
    
    # Check if fee_stance is available
    if "fee_stance" in df.columns:
        confused_count = len(df[df["fee_stance"] == "confused"])
        if confused_count > 0:
            has_confusion = True
            fee_detail = (
                f"Recurring Fee & Exit-Load Misconception: {confused_count} user reviews exhibit explicit confusion "
                "surrounding broker commissions vs statutory deductions (e.g. exit load, AMC contract note fees)."
            )
        else:
            has_confusion = len(misconceptions) > 0
            fee_detail = (
                f"Recurring Exit-Load Misconception: {len(misconceptions)} users mistakenly attribute "
                "statutory charges to hidden brokerage cuts by Groww."
            )
    else:
        has_confusion = len(misconceptions) > 0
        if has_confusion:
            fee_detail = (
                f"Recurring Exit-Load Misconception: {len(misconceptions)} users mistakenly attribute "
                "AMC-mandated exit load deductions to hidden brokerage charges levied directly by Groww."
            )
        else:
            fee_detail = "No recurring fee confusion identified in the loaded corpus."

    return {
        "total_reviews": total,
        "theme_counts": counts,
        "theme_percentages": percentages,
        "top_themes": top_3,
        "verbatim_quotes": quotes[:3],
        "fee_confusion_detected": has_confusion,
        "fee_confusion_detail": fee_detail,
        "date_min": df["date"].min().strftime("%Y-%m-%d"),
        "date_max": df["date"].max().strftime("%Y-%m-%d")
    }
