FICHIER = "README.md"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH 1 — Publish flow : ajout de l'etape emoji
# ============================================================
ancien1 = """### Publish flow
1. `extraire_introduction_article()` parses the article's HTML and extracts the first `<p>` as the post message (truncated cleanly via `tronquer_proprement()`, shared with the SEO meta description logic)
2. If extraction fails (no paragraph found), `generer_legende_facebook()` falls back to a Claude-generated caption
3. `publier_facebook()` posts to `POST /{page-id}/feed` with `message` + `link` (Graph API v21.0)
4. Every attempt — success or failure — is logged to BigQuery via `logger_publication_facebook_bq()`"""

nouveau1 = """### Publish flow
1. `extraire_introduction_article()` parses the article's HTML (via `html.unescape()` for clean entity decoding) and extracts the first `<p>` as the post message (truncated cleanly via `tronquer_proprement()`, shared with the SEO meta description logic)
2. If extraction fails (no paragraph found), `generer_legende_facebook()` falls back to a Claude-generated caption
3. A fixed, silo-specific emoji is prefixed to the message (`SILO_EMOJIS` dict — deterministic, no extra AI call, applies uniformly to both the extracted-intro and AI-fallback paths)
4. `publier_facebook()` posts to `POST /{page-id}/feed` with `message` + `link` (Graph API v21.0)
5. Every attempt — success or failure — is logged to BigQuery via `logger_publication_facebook_bq()`"""

if ancien1 not in contenu:
    print("❌ PATCH 1 (Publish flow) : bloc non trouve")
else:
    contenu = contenu.replace(ancien1, nouveau1)
    print("✅ PATCH 1 (Publish flow) : etape emoji ajoutee")

# ============================================================
# PATCH 2 — Token renewal : incident du jour + statut System User
# ============================================================
ancien2 = """### ⚠️ Token renewal — currently manual
The Page access token expires after **~60 days**. There is **no automatic renewal mechanism yet** — when it expires, Facebook publishing will silently fail (logged as an error in `historique_publications_facebook`, but won't block WordPress publishing). To renew manually:
1. Generate a fresh User token via Graph API Explorer (with the 3 permissions above)
2. Exchange it for a long-lived token (`oauth/access_token?grant_type=fb_exchange_token...`)
3. Fetch the Page token via `/me/accounts`
4. Update the secret: `echo -n "NEW_TOKEN" | gcloud secrets versions add FACEBOOK_PAGE_ACCESS_TOKEN --data-file=-`

*Possible future improvement: a scheduled Cloud Function that refreshes the token automatically before expiry, removing the need for manual renewal every ~60 days.*"""

nouveau2 = """### ⚠️ Token renewal — currently manual
The Page access token expires after **~60 days**. There is **no automatic renewal mechanism yet** — when it expires, Facebook publishing fails silently in the daily run (logged as an error in `historique_publications_facebook`, but doesn't block WordPress publishing).

**Real incident (28 July 2026):** the token in place expired within hours instead of 60 days, because the intermediate long-lived exchange step wasn't verified before deriving the Page token. All 5 same-day articles failed to post; a corrected token was generated and the 5 posts were manually republished (with proper HTML entity decoding via `html.unescape()`, fixing a display bug from the ad-hoc catch-up script). **Lesson learned: always confirm `expires_in` is ~5,180,000s in the intermediate exchange response before proceeding to `/me/accounts`.**

Current token valid until **~end of September 2026**. To renew manually:
1. Generate a fresh User token via Graph API Explorer (with the 3 permissions above)
2. Exchange it for a long-lived token (`oauth/access_token?grant_type=fb_exchange_token...`) — **verify `expires_in` ≈ 5,180,000 before continuing**
3. Fetch the Page token via `/me/accounts`
4. Update the secret: `echo -n "NEW_TOKEN" | gcloud secrets versions add FACEBOOK_PAGE_ACCESS_TOKEN --data-file=-`

**Real fix in progress:** migrating to a **Meta System User token** (Business Settings → Users → System Users), which never expires — the correct long-term solution for server-to-server publishing, avoiding this renewal cycle entirely. Blocked as of 28 July 2026: System User creation requires **Business Portfolio verification** (currently "Unverified"), a multi-day process similar to the D-U-N-S request already underway. **Deferred until after D-U-N-S validation**, then to be tackled together."""

if ancien2 not in contenu:
    print("❌ PATCH 2 (Token renewal) : bloc non trouve")
else:
    contenu = contenu.replace(ancien2, nouveau2)
    print("✅ PATCH 2 (Token renewal) : incident + statut System User ajoutes")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
