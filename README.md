# 📊 ICICI HFC Rate Tracker

Automatically tracks ICICI Home Finance FD interest rates daily and emails you whenever rates change.

**Built with:** Python + GitHub Actions (runs free, forever, no server needed)

---

## ⚡ 5-Minute Setup Guide

### Step 1 — Create the Repository

1. Go to [github.com](https://github.com) and sign in
2. Click **"+"** (top right) → **"New repository"**
3. Name it: `icici-rate-tracker`
4. Set visibility to **Public**
5. Check **"Add a README file"**
6. Click **"Create repository"**

---

### Step 2 — Upload the Files

Upload these files to your repository in the exact folder structure:

```
icici-rate-tracker/
├── scraper.py
├── requirements.txt
├── data/
│   └── rates_history.json
└── .github/
    └── workflows/
        └── rate-tracker.yml
```

**How to upload:**
- Click **"Add file"** → **"Upload files"** for each file
- For folders like `.github/workflows/`, use **"Create new file"** and type the full path:
  `.github/workflows/rate-tracker.yml` — GitHub will auto-create the folders

---

### Step 3 — Set Up Gmail App Password

You need a Gmail **App Password** (not your regular password):

1. Go to your Google Account → **Security**
2. Enable **2-Step Verification** (if not already on)
3. Go to **Security** → **App Passwords**
4. Select app: **Mail**, device: **Other** → type "Rate Tracker"
5. Click **Generate** → copy the 16-character password shown

---

### Step 4 — Add GitHub Secrets

1. In your repository, go to **Settings** → **Secrets and variables** → **Actions**
2. Click **"New repository secret"** and add these 3 secrets:

| Secret Name      | Value                              |
|------------------|------------------------------------|
| `GMAIL_SENDER`   | Your Gmail address (e.g. you@gmail.com) |
| `GMAIL_PASSWORD` | The 16-char App Password from Step 3 |
| `NOTIFY_EMAIL`   | Email where you want alerts sent   |

---

### Step 5 — Test It!

1. Go to the **"Actions"** tab in your repository
2. Click **"ICICI HFC Rate Tracker"** in the left sidebar
3. Click **"Run workflow"** → **"Run workflow"** (green button)
4. Watch it run — takes about 30 seconds
5. Check your email!

---

## 📅 Schedule

The tracker runs automatically every day at **9:00 AM IST**.

To change the time, edit `.github/workflows/rate-tracker.yml` and update the cron line:
```yaml
- cron: "30 3 * * *"   # 3:30 AM UTC = 9:00 AM IST
```
Use [crontab.guru](https://crontab.guru) to generate cron expressions.

---

## 📧 What the Alert Email Looks Like

When a rate changes, you'll receive an email with:
- **What changed** — tenure, payout type, old rate vs new rate with ▲/▼ indicator
- **Full current rate card** — all tenures and payout types

If nothing changes, no email is sent (no spam!).

---

## 📁 Rate History

Every time the tracker runs, it saves the latest rates to `data/rates_history.json`
and commits it back to the repository. This gives you a full audit trail of every
rate change over time, visible in your repository's commit history.

---

## 🔧 Troubleshooting

| Problem | Fix |
|---------|-----|
| Workflow not running | Check Actions tab → enable Actions if prompted |
| Email not received | Check Gmail spam folder; verify App Password is correct |
| Scraper fails | Check Actions log for errors; ICICI may have changed their page |
| App Password not working | Make sure 2FA is enabled on your Google account |

---

## ⚙️ Tracked Rates

| Tenure | Cumulative | Monthly | Quarterly | Yearly |
|--------|-----------|---------|-----------|--------|
| Special – 45 months | ✅ | ✅ | ✅ | ✅ |
| Special – 39 months | ✅ | ✅ | ✅ | ✅ |
| 48 to <60 months | ✅ | ✅ | ✅ | ✅ |
| 36 to <48 months | ✅ | ✅ | ✅ | ✅ |
| 24 to <36 months | ✅ | ✅ | ✅ | ✅ |
| 12 to <24 months | ✅ | ✅ | ✅ | ✅ |
