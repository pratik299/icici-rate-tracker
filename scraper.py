import requests
import json
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── Config (set these as GitHub Secrets) ────────────────────────────
GMAIL_SENDER   = os.environ.get("GMAIL_SENDER")    # your Gmail address
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")  # Gmail App Password
NOTIFY_EMAIL   = os.environ.get("NOTIFY_EMAIL")    # where to send alerts

RATES_FILE = "data/rates_history.json"

# ── Scrape FD rates ──────────────────────────────────────────────────
def scrape_fd_rates():
    url = "https://www.icicihfc.com/en/fixed-deposit"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; RateTracker/1.0)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    html = resp.text

    # Parse the FD interest rate table from page HTML
    import re
    rates = {}

    # Tenures and their patterns in the page
    tenure_map = {
        "Special – 45 months": r"Special.*?45 months.*?(\d+\.\d+)%.*?(\d+\.\d+)%.*?(\d+\.\d+)%.*?(\d+\.\d+)%",
        "Special – 39 months": r"Special.*?39 months.*?(\d+\.\d+)%.*?(\d+\.\d+)%.*?(\d+\.\d+)%.*?(\d+\.\d+)%",
        "48 to <60 months":    r"48 to.*?60 months.*?(\d+\.\d+)%.*?(\d+\.\d+)%.*?(\d+\.\d+)%.*?(\d+\.\d+)%",
        "36 to <48 months":    r"36 to.*?48 months.*?(\d+\.\d+)%.*?(\d+\.\d+)%.*?(\d+\.\d+)%.*?(\d+\.\d+)%",
        "24 to <36 months":    r"24 to.*?36 months.*?(\d+\.\d+)%.*?(\d+\.\d+)%.*?(\d+\.\d+)%.*?(\d+\.\d+)%",
        "12 to <24 months":    r"12 to.*?24 months.*?(\d+\.\d+)%.*?(\d+\.\d+)%.*?(\d+\.\d+)%.*?(\d+\.\d+)%",
    }

    # Simpler approach: find rate table section and extract all percentages in order
    # The page renders: Tenure | Cumulative | Monthly | Quarterly | Yearly
    table_section = re.search(
        r"FD Interest Rates.*?(?=sectionid|Eligibility|FD Criteria)",
        html, re.DOTALL | re.IGNORECASE
    )

    if table_section:
        section_html = table_section.group(0)
        # Extract all percentage values in the order they appear
        all_rates = re.findall(r"(\d+\.\d+)%", section_html)

        tenures = [
            "Special – 45 months",
            "Special – 39 months",
            "48 to <60 months",
            "36 to <48 months",
            "24 to <36 months",
            "12 to <24 months",
        ]

        # Each tenure has 4 values: Cumulative, Monthly, Quarterly, Yearly
        for i, tenure in enumerate(tenures):
            base = i * 4
            if base + 3 < len(all_rates):
                rates[tenure] = {
                    "cumulative": all_rates[base] + "%",
                    "monthly":    all_rates[base + 1] + "%",
                    "quarterly":  all_rates[base + 2] + "%",
                    "yearly":     all_rates[base + 3] + "%",
                }

    # Fallback: scrape from the FD calculator widget data embedded in homepage
    if not rates:
        home = requests.get("https://www.icicihfc.com/", headers=headers, timeout=15).text
        fd_rates = re.findall(r"(\d+\.\d+)\s*\n\s*(\d+)\s*\n\s*true", home)
        for rate, tenure_months, *_ in fd_rates:
            rates[f"{tenure_months} months"] = {"cumulative": rate + "%"}

    return rates


# ── Scrape Home Loan rates ───────────────────────────────────────────
def scrape_hl_rates():
    url = "https://www.icicihfc.com/en/loans/home-loan"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; RateTracker/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        html = resp.text

        import re
        rates = {}

        # Look for interest rate mentions like "8.75%" or "Starting from X%"
        rate_matches = re.findall(
            r"(?:interest rate|rate of interest|starting from|from|@)\s*[\:\-]?\s*(\d+\.?\d*)\s*%",
            html, re.IGNORECASE
        )
        if rate_matches:
            rates["home_loan_rate_mentions"] = list(set(rate_matches))

        # Also look for ROI table patterns
        roi_section = re.search(
            r"(?:Interest Rate|ROI|Rate of Interest).*?(\d+\.?\d*%.*?\d+\.?\d*%)",
            html, re.DOTALL | re.IGNORECASE
        )
        if roi_section:
            rates["roi_section_snippet"] = roi_section.group(1)[:200]

        return rates
    except Exception as e:
        return {"error": str(e)}


# ── Load / save history ──────────────────────────────────────────────
def load_history():
    if os.path.exists(RATES_FILE):
        with open(RATES_FILE) as f:
            return json.load(f)
    return {}


def save_history(data):
    os.makedirs(os.path.dirname(RATES_FILE), exist_ok=True)
    with open(RATES_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── Diff ─────────────────────────────────────────────────────────────
def find_changes(old, new):
    changes = []
    for tenure, new_vals in new.items():
        old_vals = old.get(tenure, {})
        for payout_type, new_rate in new_vals.items():
            old_rate = old_vals.get(payout_type, "N/A")
            if old_rate != new_rate:
                changes.append({
                    "tenure":      tenure,
                    "payout_type": payout_type,
                    "old_rate":    old_rate,
                    "new_rate":    new_rate,
                })
    return changes


# ── Email ────────────────────────────────────────────────────────────
def send_email(changes, current_rates):
    if not all([GMAIL_SENDER, GMAIL_PASSWORD, NOTIFY_EMAIL]):
        print("⚠️  Email credentials not set. Skipping email.")
        return

    subject = f"🚨 ICICI HFC Rate Change Detected – {datetime.now().strftime('%d %b %Y')}"

    # Build HTML email
    changes_rows = ""
    for c in changes:
        direction = "🔺" if float(c["new_rate"].strip("%")) > float(c["old_rate"].strip("%")) if c["old_rate"] != "N/A" else True else "🔻"
        changes_rows += f"""
        <tr>
            <td style="padding:8px;border:1px solid #ddd;">{c['tenure']}</td>
            <td style="padding:8px;border:1px solid #ddd;text-transform:capitalize">{c['payout_type']}</td>
            <td style="padding:8px;border:1px solid #ddd;color:#888;">{c['old_rate']}</td>
            <td style="padding:8px;border:1px solid #ddd;font-weight:bold;color:#003087;">{c['new_rate']} {direction}</td>
        </tr>"""

    all_rates_rows = ""
    for tenure, vals in current_rates.items():
        all_rates_rows += f"""
        <tr>
            <td style="padding:8px;border:1px solid #ddd;">{tenure}</td>
            <td style="padding:8px;border:1px solid #ddd;">{vals.get('cumulative','—')}</td>
            <td style="padding:8px;border:1px solid #ddd;">{vals.get('monthly','—')}</td>
            <td style="padding:8px;border:1px solid #ddd;">{vals.get('quarterly','—')}</td>
            <td style="padding:8px;border:1px solid #ddd;">{vals.get('yearly','—')}</td>
        </tr>"""

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:700px;margin:auto;">
      <div style="background:#003087;color:white;padding:20px;border-radius:8px 8px 0 0;">
        <h2 style="margin:0">ICICI HFC Interest Rate Change Alert</h2>
        <p style="margin:4px 0 0;opacity:0.8">{datetime.now().strftime('%A, %d %B %Y')}</p>
      </div>
      <div style="padding:20px;border:1px solid #ddd;border-top:none;">

        <h3 style="color:#003087">What Changed</h3>
        <table style="width:100%;border-collapse:collapse;font-size:14px;">
          <tr style="background:#003087;color:white;">
            <th style="padding:8px;text-align:left;">Tenure</th>
            <th style="padding:8px;text-align:left;">Payout Type</th>
            <th style="padding:8px;text-align:left;">Old Rate</th>
            <th style="padding:8px;text-align:left;">New Rate</th>
          </tr>
          {changes_rows}
        </table>

        <h3 style="color:#003087;margin-top:24px">Current Full Rate Card</h3>
        <table style="width:100%;border-collapse:collapse;font-size:14px;">
          <tr style="background:#003087;color:white;">
            <th style="padding:8px;text-align:left;">Tenure</th>
            <th style="padding:8px;">Cumulative</th>
            <th style="padding:8px;">Monthly</th>
            <th style="padding:8px;">Quarterly</th>
            <th style="padding:8px;">Yearly</th>
          </tr>
          {all_rates_rows}
        </table>

        <p style="margin-top:20px;font-size:12px;color:#888;">
          This alert was generated automatically by your ICICI HFC Rate Tracker.<br>
          Source: <a href="https://www.icicihfc.com/en/fixed-deposit">icicihfc.com/en/fixed-deposit</a>
        </p>
      </div>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_SENDER
    msg["To"]      = NOTIFY_EMAIL
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_SENDER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_SENDER, NOTIFY_EMAIL, msg.as_string())

    print(f"✅ Alert email sent to {NOTIFY_EMAIL}")


# ── Main ─────────────────────────────────────────────────────────────
def main():
    print(f"🔍 Scraping ICICI HFC rates at {datetime.now().isoformat()}")

    current_fd   = scrape_fd_rates()
    current_hl   = scrape_hl_rates()

    print(f"✅ Scraped {len(current_fd)} FD tenures")

    history = load_history()
    last_fd = history.get("fd_rates", {})

    changes = find_changes(last_fd, current_fd)

    # Save updated history
    history["fd_rates"]      = current_fd
    history["hl_rates"]      = current_hl
    history["last_checked"]  = datetime.now().isoformat()
    history["last_changed"]  = datetime.now().isoformat() if changes else history.get("last_changed", "Never")
    save_history(history)

    if changes:
        print(f"🚨 {len(changes)} rate change(s) detected!")
        for c in changes:
            print(f"   {c['tenure']} [{c['payout_type']}]: {c['old_rate']} → {c['new_rate']}")
        send_email(changes, current_fd)
    else:
        print("✅ No rate changes detected. All quiet.")


if __name__ == "__main__":
    main()
