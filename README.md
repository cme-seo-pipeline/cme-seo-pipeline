# 🤖 CME Content Pipeline — AI-Powered SEO Content Generation

> **Automated end-to-end pipeline** for generating SEO-optimized articles on [comprendre-mon-energie.fr](https://www.comprendre-mon-energie.fr)  
> Deployed on **Google Cloud Run** · Scheduled via **Cloud Scheduler** · Powered by **Claude (Anthropic)**

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLOUD SCHEDULER                          │
│                     (Cron · Automatic trigger)                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     GOOGLE CLOUD RUN                            │
│                        server.py                                │
│                    (FastAPI / HTTP API)                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       pipeline.py                               │
│                                                                 │
│   1. 🕷️  SCRAPING          → Collect competitor data & SERPs   │
│   2. 🧠  CLAUDE API        → Generate SEO article              │
│   3. 🔗  INTERNAL LINKING  → Auto maillage interne             │
│   4. 📊  SCHEMA / TABLES   → Structured data & rich content    │
│   5. 🖼️  IMAGES            → Auto-generated visuals            │
│   6. 📝  H1/H2 STRUCTURE   → Semantic hierarchy                │
│   7. 📤  WORDPRESS API     → Auto-publish via REST API         │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              comprendre-mon-energie.fr (WordPress)              │
│         Article published · SEO-ready · 100% automated         │
└─────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Tech Stack

| Component | Technology |
|---|---|
| **Language** | Python 3.11 |
| **API Server** | FastAPI |
| **AI Model** | Claude (Anthropic API) |
| **Scraping** | Custom scraper |
| **CMS** | WordPress REST API |
| **Containerization** | Docker |
| **Hosting** | Google Cloud Run |
| **Scheduling** | Google Cloud Scheduler |
| **CI/CD** | GitHub → Cloud Run (auto-deploy) |

---

## 🚀 What it generates — per article

Each pipeline run produces a **fully SEO-optimized article** including:

- ✅ **H1 / H2 structure** — semantic hierarchy auto-generated
- ✅ **Internal linking** — automatic maillage interne across the site
- ✅ **Schema.org** — structured data (FAQ, Article, BreadcrumbList)
- ✅ **Rich tables** — comparison tables with real market data
- ✅ **Images** — auto-generated visuals with alt tags
- ✅ **Semantic richness** — LSI keywords, entities, topical coverage
- ✅ **WordPress publish** — auto-posted via REST API with categories & tags

---

## 🌐 Live Result

→ [comprendre-mon-energie.fr](https://www.comprendre-mon-energie.fr)  
→ [SEO Architecture — Interactive graph (119 URLs)](https://cme-seo-pipeline.github.io/seo-architecture-cme/)

---

## 📁 Project Structure

```
├── Dockerfile           # Container config for Cloud Run
├── server.py            # FastAPI server — HTTP trigger endpoint
├── pipeline.py          # Core pipeline logic
│   ├── scraper          # Web scraping module
│   ├── claude_client    # Anthropic API integration
│   ├── wp_publisher     # WordPress REST API publisher
│   └── seo_formatter    # H1/H2, schema, internal links
└── requirements.txt     # Python dependencies
```

---

## 🔒 Note

This repository is **private** — source code is not publicly available.  
For collaboration or inquiries: [blal3154@gmail.com](mailto:blal3154@gmail.com)

---

*Built by [Oussama Blal](https://www.comprendre-mon-energie.fr) · 2026*
