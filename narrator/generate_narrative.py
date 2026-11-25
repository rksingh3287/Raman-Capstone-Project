import json
import os


SYSTEM_PROMPT = (
    "You are a senior data analyst writing for Mamaearth's regional ops and finance heads. "
    "Use three labeled sections: Situation, Complication, and Resolution. "
    "Every number in your response must come from the supplied findings and keep the exact same value; do not invent any statistics."
)


def build_prompt(findings):
    rr = findings["return_rate_by_payment"]
    seg = findings["highest_risk_segment"]
    peak = findings["true_peak_month"]
    inf = findings["outlier_inflated_month"]

    return (
        "Write an executive summary (~250 words) in Situation-Complication-Resolution format using only these numbers:\n"
        f"- Cleaned total revenue: INR {findings['cleaned_total_revenue_inr']:.2f} "
        f"(raw SQL revenue: INR {findings['raw_total_revenue_inr']:.2f}, "
        f"duplicate delta: INR {findings['duplicate_reconciliation_delta_inr']:.2f})\n"
        f"- Return rates: COD {rr['COD']}%, UPI {rr['UPI']}%, CARD {rr['CARD']}%\n"
        f"- Highest-risk segment: {seg['payment_method']} + Tier-{seg['city_tier']} at {seg['return_rate_pct']}%\n"
        f"- True peak month: {peak['month']} (March) at INR {peak['revenue_inr']:.2f}\n"
        f"- Outlier-inflated month: {inf['month']} was INR {inf['apparent_revenue_inr']:.2f} before removing outliers, "
        f"and INR {inf['corrected_revenue_inr']:.2f} after.\n"
    )


def generate_scr_narrative(findings: dict) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return {"status": "error", "narrative": None, "message": "No API key found"}

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=30000),  # 15s timeout
        )
        # temperature=0.0 because this is a factual business report, not creative writing
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0,
            max_output_tokens=500,
        )
        resp = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=build_prompt(findings),
            config=config,
        )
        tokens = getattr(getattr(resp, "usage_metadata", None), "total_token_count", None)
        return {"status": "success", "narrative": resp.text, "tokens": tokens}
    except Exception as err:
        return {"status": "error", "narrative": None, "message": str(err)}


def generate_scr_narrative_offline(findings: dict) -> dict:
    rev = findings["cleaned_total_revenue_inr"]
    raw_rev = findings["raw_total_revenue_inr"]
    delta = findings["duplicate_reconciliation_delta_inr"]
    rr = findings["return_rate_by_payment"]
    seg = findings["highest_risk_segment"]
    peak = findings["true_peak_month"]
    inf = findings["outlier_inflated_month"]

    text = (
        "Situation\n"
        f"From January to June 2026, Mamaearth generated INR {rev:,.2f} in cleaned revenue across 175 orders. "
        f"Comparing against the raw SQL total of INR {raw_rev:,.2f} showed a difference of INR {delta:,.2f} "
        f"from 5 duplicate orders. After removing two bulk outlier orders that pushed {inf['month']} from "
        f"INR {inf['corrected_revenue_inr']:,.2f} up to INR {inf['apparent_revenue_inr']:,.2f}, "
        f"March ({peak['month']}) is the actual peak month with INR {peak['revenue_inr']:,.2f} in revenue.\n\n"
        "Complication\n"
        f"Returns are much higher on COD orders at {rr['COD']:.1f}%, compared to {rr['CARD']:.1f}% for CARD "
        f"and {rr['UPI']:.1f}% for UPI. Looking closer by city tier, {seg['payment_method']} orders in "
        f"Tier-{seg['city_tier']} cities have the highest return rate at {seg['return_rate_pct']:.1f}%. "
        "Higher discounts also do not lower returns.\n\n"
        "Resolution\n"
        f"Ops and finance teams should focus on {seg['payment_method']} + Tier-{seg['city_tier']} orders "
        f"({seg['return_rate_pct']:.1f}% return rate) by adding COD order confirmation or prepaid nudges "
        f"toward CARD ({rr['CARD']:.1f}%) and UPI ({rr['UPI']:.1f}%), and fix the checkout double-submit "
        f"issue causing the INR {delta:,.2f} duplicate discrepancy."
    )
    return {"status": "success", "narrative": text, "tokens": 0}


def check_numeric_accuracy(narrative: str, findings: dict) -> bool:
    clean_text = narrative.replace(",", "")
    rev = findings["cleaned_total_revenue_inr"]
    cod = findings["return_rate_by_payment"]["COD"]
    seg = findings["highest_risk_segment"]["return_rate_pct"]
    delta = findings["duplicate_reconciliation_delta_inr"]
    peak = findings["true_peak_month"]["revenue_inr"]

    tests = [
        ("Cleaned revenue (97358.30)", f"{rev:.2f}" in clean_text or f"{rev:.1f}" in clean_text),
        ("COD return rate (44.4)", f"{cod:.1f}" in clean_text),
        ("COD + Tier-2 return rate (54.5)", f"{seg:.1f}" in clean_text),
        ("Duplicate delta (2501.90)", f"{delta:.2f}" in clean_text or f"{delta:.1f}" in clean_text),
        ("March peak (20318.90)", "March" in narrative and (f"{peak:.2f}" in clean_text or f"{peak:.1f}" in clean_text)),
    ]

    ok = True
    for name, passed in tests:
        print(f"{'PASS' if passed else 'FAIL'} - {name}")
        if not passed:
            ok = False
    return ok


if __name__ == "__main__":
    with open("narrator/findings.json", encoding="utf-8") as f:
        findings = json.load(f)

    out = generate_scr_narrative(findings)
    if out["status"] == "error":
        print("Using offline fallback:", out["message"])
        out = generate_scr_narrative_offline(findings)

    print("\n" + out["narrative"] + "\n")
    assert check_numeric_accuracy(out["narrative"], findings)
