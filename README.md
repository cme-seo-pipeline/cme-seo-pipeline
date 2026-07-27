# 🤖 CME Ecosystem — AI-Powered SEO Content & Lead Generation

> **Automated end-to-end ecosystem** for content generation, lead capture, and eligibility simulation on [comprendre-mon-energie.fr](https://www.comprendre-mon-energie.fr)
> Deployed on **Google Cloud Run** · Scheduled via **Cloud Scheduler** · Powered by **Claude (Anthropic)**

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLOUD SCHEDULER                          │
│                  (Cron · 05h00 Paris · Lun-Dim)                 │
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
│   6. 🖼️  IMAGES            → Auto-generated visuals (DALL·E)      │
│   7. 🎯  CTA INJECTION     → Silo-based link to matching simulator│
│   8. 📤  WORDPRESS API     → Auto-publish via REST API            │
│   9. 📘  FACEBOOK PUBLISH  → Auto-post to Page (article intro)    │
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
| **Social Publishing** | Meta Graph API (Facebook Page) |
| **Automation** | Google Apps Script (GSC/GA4 sync, lead sheets) |
| **PDF Generation** | jsPDF (client-side, base64-delivered) |
| **Containerization** | Docker |
| **Hosting** | Google Cloud Run |
| **Scheduling** | Google Cloud Scheduler |
| **Secrets** | Google Secret Manager |
| **CI/CD** | GitHub → Cloud Run (auto-deploy) |

---

## 🧠 Content Pipeline (`pipeline/`)

Fully automated SEO article generation, 3 articles/day, 5 silos (Gaz, Rénovation Énergétique, Aide Énergétique, Solaire, Électricité).

**Opportunity-driven selection** — instead of publishing on a fixed rotation, the pipeline queries `03_final.seo_opportunities`, a BigQuery view combining:
- **Google Search Console** data (position, impressions, CTR) — synced daily via Apps Script
- **GA4** engagement data (sessions, bounce rate)
- **Publication history** (anti-duplicate, freshness scoring)

Each article is scored on ranking potential and automatically gets a **CTA block** linking to the matching simulator based on its silo. The CTA block includes a `clear:both` defensive wrapper to prevent visual overlap when the AI-generated article ends with an HTML table.

Titles and meta descriptions are generated within strict SEO-friendly bounds (50–60 / 150–160 characters) and, as a safety net, truncated at the nearest word boundary if the model ever overshoots — never mid-word.

---

## 📘 Meta / Facebook Integration (`pipeline/`)

Every article published to WordPress is automatically cross-posted to the CME Facebook Page, using the article's **real introduction paragraph** as the post description (not a separately generated marketing blurb) — Facebook auto-generates the link preview (image, title) from the article's Open Graph tags.

### Storage
Credentials live in **Google Secret Manager**, mounted as env vars on Cloud Run — same pattern as `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `WP_APP_PASSWORD`:

| Secret | Purpose |
|---|---|
| `FACEBOOK_PAGE_ID` | Target Page ID |
| `FACEBOOK_PAGE_ACCESS_TOKEN` | Long-lived Page access token (~60 days) |

### Publish flow
1. `extraire_introduction_article()` parses the article's HTML and extracts the first `<p>` as the post message (truncated cleanly via `tronquer_proprement()`, shared with the SEO meta description logic)
2. If extraction fails (no paragraph found), `generer_legende_facebook()` falls back to a Claude-generated caption
3. `publier_facebook()` posts to `POST /{page-id}/feed` with `message` + `link` (Graph API v21.0)
4. Every attempt — success or failure — is logged to BigQuery via `logger_publication_facebook_bq()`

### Testing
Validated manually via the **Graph API Explorer** (`developers.facebook.com/tools/explorer`) before wiring into the pipeline: generated a User token with `pages_show_list` + `pages_manage_posts` + `pages_read_engagement`, exchanged it for a long-lived token, fetched the Page token via `/me/accounts`, and confirmed a real post (`HTTP 200`, returned post ID) before enabling automatic publishing.

### ⚠️ Token renewal — currently manual
The Page access token expires after **~60 days**. There is **no automatic renewal mechanism yet** — when it expires, Facebook publishing will silently fail (logged as an error in `historique_publications_facebook`, but won't block WordPress publishing). To renew manually:
1. Generate a fresh User token via Graph API Explorer (with the 3 permissions above)
2. Exchange it for a long-lived token (`oauth/access_token?grant_type=fb_exchange_token...`)
3. Fetch the Page token via `/me/accounts`
4. Update the secret: `echo -n "NEW_TOKEN" | gcloud secrets versions add FACEBOOK_PAGE_ACCESS_TOKEN --data-file=-`

*Possible future improvement: a scheduled Cloud Function that refreshes the token automatically before expiry, removing the need for manual renewal every ~60 days.*

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
  ├── historique_publications          Every article ever published (silo, slug, post_id)
  ├── historique_publications_facebook Every Facebook post attempt (success/failure, post id, message used)
  ├── historique_clics_comparateur     Anonymous comparateur click tracking
  ├── leads_convertis                  Converted leads with contact info, all 3 tools
  ├── analyse_concurrents              Scraped competitor data per run
  ├── briefs_editoriaux                Generated editorial briefs
  ├── url_mapping                      Legacy URL → current silo/sous-silo mapping (post-migration)
  ├── sous_silos_strategiques          Strategic sub-silo reference table
  └── vue_arbre_performance (view)     Silo → Sous-silo → Article performance rollup for Looker Studio
                                       (GSC impressions/clicks/position + conversions, full-site coverage)
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
├── bigquery/                     # Standalone SQL: views, migrations, one-off data fixes
├── scripts-maintenance/          # One-off migration/fix scripts (slug collisions, CTA backfill)
└── maj-trimestrielle/            # Quarterly regulated tariff updater
```

---

## 🔒 Note

This repository is **private** — source code is not publicly available.
For collaboration or inquiries: [oussama.blal@comprendre-mon-energie.fr](mailto:oussama.blal@comprendre-mon-energie.fr)

---

*Built by [Oussama Blal](https://www.comprendre-mon-energie.fr) · 2026*
