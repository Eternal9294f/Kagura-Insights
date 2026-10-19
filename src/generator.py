from datetime import datetime
from typing import Dict, Tuple

OFFICIAL_SOURCES = [
    {
        "title": "Groww Official Help Center: What is Exit Load?",
        "url": "https://groww.in/help/mutual-funds/order/what-is-exit-load--71"
    },
    {
        "title": "Groww Knowledge Base: How Exit Load is Calculated",
        "url": "https://groww.in/p/exit-load-in-mutual-funds"
    }
]

def generate_weekly_pulse(analysis: Dict, product_name: str = "Groww") -> Tuple[str, int]:
    total = analysis.get("total_reviews", 0)
    top_3 = analysis.get("top_themes", [])
    quotes = analysis.get("verbatim_quotes", [])

    theme_lines = "\n".join([f"- **{t[0]}**: {t[1]} reviews ({analysis['theme_percentages'].get(t[0], 0)}%)" for t in top_3])
    quote_lines = "\n".join([f'> *"{q}"*' for q in quotes[:3]])

    pulse_text = (
        f"**Weekly Product Pulse — {product_name}**\n\n"
        f"**1. Top Customer Themes (Total Analyzed: {total})**\n"
        f"{theme_lines}\n\n"
        f"**2. Voice of Customer (Genuine Quotes)**\n"
        f"{quote_lines}\n\n"
        f"**3. Key Friction Observation**\n"
        f"Users repeatedly confuse statutory AMC exit loads with unauthorized broker charges upon redemption.\n\n"
        f"**4. Actionable Recommendations**\n"
        f"1. *Pre-Redeem Estimator*: Display exact rupee exit-load deduction before redemption confirmation.\n"
        f"2. *Contextual Badge*: Clarify that exit load is retained by the AMC, not {product_name}.\n"
        f"3. *SIP Aging Tracker*: Add purchase-date tooltips identifying which SIP installments have cleared lock-in."
    )

    words = len(pulse_text.split())
    return pulse_text, words

def generate_fee_explainer(analysis: Dict, product_name: str = "Groww") -> Dict:
    today_str = datetime.now().strftime("%Y-%m-%d")

    bullets = [
        f"Exit load is a statutory fee levied by Asset Management Companies (AMCs), not by {product_name}.",
        "The fee is deducted from fund NAV only if units are redeemed before the scheme's specified holding period (typically 7 to 365 days).",
        f"{product_name} operates as a direct mutual fund platform and charges ₹0 brokerage and ₹0 commission on mutual fund redemptions.",
        "For SIP investments, exit load applies individually to each monthly installment based on its unique purchase date on a FIFO basis.",
        "Exit load proceeds are credited back into the mutual fund scheme corpus to safeguard long-term unitholders.",
        "Investors can preview applicable exit-load percentages and holding cutoff periods on each fund's detail page before placing orders."
    ]

    return {
        "title": f"Customer Clarification: Mutual Fund Exit Loads on {product_name}",
        "bullets": bullets[:6],
        "source_links": OFFICIAL_SOURCES,
        "last_checked": today_str
    }
