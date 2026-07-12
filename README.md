# 🤖 CME Ecosystem — AI-Powered SEO Content & Lead Generation

> **Automated end-to-end ecosystem** for content generation, lead capture, and eligibility simulation on [comprendre-mon-energie.fr](https://www.comprendre-mon-energie.fr)
> Deployed on **Google Cloud Run** · Scheduled via **Cloud Scheduler** · Powered by **Claude (Anthropic)**

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLOUD SCHEDULER                          │
│                  (Cron · 05h00 Paris · Lun-Ven)                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     GOOGLE CLOUD RUN                             │
│                  cme-seo-pipeline (server.py)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       pipeline.py                                │
│                                                                   │
│   1. 📂  SILO SELECTION    → BigQuery seo_opportunities (GSC+GA4) │
│   2. 🕷️  SCRAPING          → Collect competitor data & SERPs     │
│   3. 🧠  CLAUDE API        → Generate SEO article                │
│   4. 🔗  INTERNAL LINKING  → Auto maillage interne                │
│   5. 📊  SCHEMA / TABLES   → Structured data & rich content      │
│   6. 🖼️  IMAGES            → Auto-generated visuals               │
│   7. 🎯  CTA INJECTION     → Silo-based link to matching simulator│
│   8. 📤  WORDPRESS API     → Auto-publish via REST API            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              comprendre-mon-energie.fr (WordPress)               │
│    Article published + CTA → one of 3 lead-gen simulators        │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
      ☀️ Solaire      ⚡ Comparateur    🏠 Aides Rénovation
      (devis-panneau-  (comparateur-    (simulateur-aides-
       solaire)         energie)         renovation)
              │              │              │
              └──────────────┼──────────────┘
                             ▼
              ┌───────────────────────────┐
              │   Lead capture (modal)     │
              │  Email + Google Sheets +   │
              │  BigQuery (leads_convertis)│
              └───────────────────────────┘
```

---

## ⚙️ Tech Stack

| Component | Technology |
|---|---|
| **Language** | Python 3.11 / PHP (WordPress plugins) |
| **API Server** | FastAPI (pipeline) · Flask (tracking-api) |
| **AI Model** | Claude (Anthropic API) |
| **Data Warehouse** | BigQuery |
| **CMS** | WordPress REST API |
| **Automation** | Google Apps Script (GSC/GA4 sync, lead sheets) |
| **PDF Generation** | jsPDF (client-side, base64-delivered) |
| **Containerization** | Docker |
| **Hosting** | Google Cloud Run |
| **Scheduling** | Google Cloud Scheduler |
| **CI/CD** | GitHub → Cloud Run (auto-deploy) |

---

## 🧠 Content Pipeline (`pipeline/`)

Fully automated SEO article generation, 3 articles/day, 5 silos (Gaz, Rénovation Énergétique, Aide Énergétique, Solaire, Électricité).

**Opportunity-driven selection** — instead of publishing on a fixed rotation, the pipeline queries `03_final.seo_opportunities`, a BigQuery view combining:
- **Google Search Console** data (position, impressions, CTR) — synced daily via Apps Script
- **GA4** engagement data (sessions, bounce rate)
- **Publication history** (anti-duplicate, freshness scoring)

Each article is scored on ranking potential and automatically gets a **CTA block** linking to the matching simulator based on its silo.

---

## 🧮 Lead-Generation Simulators (`wordpress-plugins/`)

Three standalone WordPress plugins, each a self-contained eligibility/quote simulator with live preview, PDF export, and lead capture.

| Simulator | Covers | URL |
|---|---|---|
| ☀️ **Solaire** | Panel sizing, PVGIS production estimate, Linky (Enedis OAuth2) real consumption, ROI 25yr | `/devis-panneau-solaire/` |
| ⚡ **Comparateur Énergie** | Elec/Gaz offer comparison, EDF regulated tariff API | `/comparateur-energie-electricite-gaz/` |
| 🏠 **Aides Rénovation** | MaPrimeRénov' (official 2026 Anah barème), CEE, Éco-PTZ, reduced VAT | `/simulateur-aides-renovation-energetique/` |

**Shared architecture across all 3:**
- Vanilla JS (no framework), delivered via **base64-encoded payload** + tiny loader script — immune to JS minifiers/optimizers (LiteSpeed Cache, Autoptimize, etc.) that would otherwise corrupt large inline scripts
- Script injected via `wp_footer` hook to bypass `wpautop` content filters
- `function_exists` guards on every function — safe to reinstall without fatal errors
- Lead capture: modal form → WordPress AJAX (server-side) → email notification + Google Sheets (per-tool Apps Script) + BigQuery (`leads_convertis`)
- Client-facing PDF export (jsPDF) with CME branding and legal mentions

---

## 📡 Apps Scripts (`apps-scripts/`)

| Script | Purpose |
|---|---|
| `cme-gsc-to-bq.gs` | Daily Search Console → `01_raw.gsc_queries` |
| `cme-ga4-to-bq.gs` | Daily GA4 → `01_raw.ga4_pages` |
| `cme-comparateur-leads.gs` | Comparateur leads → dedicated Google Sheet tab |
| `cme-aides-leads.gs` | Aides simulator leads → dedicated Google Sheet tab |

---

## 📊 BigQuery Data Architecture

```
01_raw/               Raw ingested data (GSC, GA4)
03_final/              seo_opportunities — scored publication targets (GSC+GA4+history join)
04_pipeline_seo/
  ├── historique_publications         Every article ever published (silo, slug, post_id)
  ├── historique_clics_comparateur    Anonymous comparateur click tracking
  ├── leads_convertis                 Converted leads with contact info, all 3 tools
  ├── analyse_concurrents             Scraped competitor data per run
  └── briefs_editoriaux               Generated editorial briefs
```

---

## 📁 Project Structure

```
├── pipeline/                     # Content generation service (Cloud Run)
│   ├── pipeline.py
│   ├── server.py
│   ├── Dockerfile
│   └── requirements.txt
├── tracking-api/                 # Lightweight tracking service (Cloud Run)
│   ├── server.py                 # /api/log-clic, /api/log-lead, /api/tarifs
│   └── Dockerfile
├── wordpress-plugins/
│   ├── simulateur-solaire/
│   ├── comparateur-energie/
│   └── simulateur-aides/
├── apps-scripts/
├── scripts-maintenance/          # One-off migration/fix scripts (slug collisions, CTA backfill)
└── maj-trimestrielle/            # Quarterly regulated tariff updater
```

---

## 🔒 Note

This repository is **private** — source code is not publicly available.
For collaboration or inquiries: [oussama.blal@comprendre-mon-energie.fr](mailto:oussama.blal@comprendre-mon-energie.fr)

---

*Built by [Oussama Blal](https://www.comprendre-mon-energie.fr) · 2026*
