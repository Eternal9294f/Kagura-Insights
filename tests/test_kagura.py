import os
import json
import pytest
import pandas as pd
from src.analysis import validate_and_load_reviews, filter_by_weeks, analyze_corpus
from src.generator import generate_weekly_pulse, generate_fee_explainer
from src.mcp_client import KaguraMCPClient

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SAMPLE_CSV = os.path.join(BASE_DIR, "data", "reviews.csv")

def test_csv_validation_and_windowing():
    df, msg = validate_and_load_reviews(SAMPLE_CSV)
    assert not df.empty
    assert len(df) >= 60
    assert "review_text" in df.columns
    filtered = filter_by_weeks(df, weeks=10)
    assert len(filtered) > 0

def test_theme_cap_and_percentages():
    df, _ = validate_and_load_reviews(SAMPLE_CSV)
    analysis = analyze_corpus(df)
    assert len(analysis["theme_counts"]) <= 5
    assert len(analysis["top_themes"]) == 3
    assert 99.0 <= sum(analysis["theme_percentages"].values()) <= 101.0

def test_verbatim_quote_grounding():
    df, _ = validate_and_load_reviews(SAMPLE_CSV)
    analysis = analyze_corpus(df)
    quotes = analysis["verbatim_quotes"]
    assert len(quotes) == 3
    corpus_texts = df["review_text"].tolist()
    for q in quotes:
        assert q in corpus_texts, f"Hallucinated quote detected: {q}"

def test_fee_confusion_vs_complaint():
    df, _ = validate_and_load_reviews(SAMPLE_CSV)
    analysis = analyze_corpus(df)
    assert analysis["fee_confusion_detected"] is True

def test_weekly_pulse_word_count_and_recommendations():
    df, _ = validate_and_load_reviews(SAMPLE_CSV)
    analysis = analyze_corpus(df)
    pulse, words = generate_weekly_pulse(analysis, "Groww")
    assert words <= 250
    assert "Actionable Recommendations" in pulse

def test_fee_explainer_bullet_and_link_rules():
    df, _ = validate_and_load_reviews(SAMPLE_CSV)
    analysis = analyze_corpus(df)
    explainer = generate_fee_explainer(analysis, "Groww")
    assert len(explainer["bullets"]) <= 6
    assert len(explainer["source_links"]) >= 2
    assert "last_checked" in explainer

def test_mcp_workflow_and_payload_schemas():
    df, _ = validate_and_load_reviews(SAMPLE_CSV)
    analysis = analyze_corpus(df)
    pulse, _ = generate_weekly_pulse(analysis, "Groww")
    explainer = generate_fee_explainer(analysis, "Groww")

    client = KaguraMCPClient()
    staged = client.stage_payloads(pulse, explainer, analysis, "Groww")
    assert "notes_payload" in staged
    res_n, res_d = client.execute_approved_workflow(staged)
    assert os.path.exists(res_n["destination"])
    for d in res_d["destinations"]:
        assert os.path.exists(d)
