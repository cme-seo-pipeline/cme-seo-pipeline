"""
CME — Diagnostic LECTURE SEULE : caracteriser le trafic quotidien en
provenance de Chine signale par l'operateur dans Microsoft Clarity
("des sessions chaque jour, sans parcours reel").

La table synchronisee `01_raw.ga4_pages` (apps-scripts/cme-ga4-to-bq.gs)
n'a PAS de dimension pays (seulement pagePath + date) -- impossible de
repondre a la question avec les donnees deja en BigQuery. Ce script
appelle donc directement l'API GA4 Data API (property 528487832) avec le
meme compte de service que le pipeline (GOOGLE_APPLICATION_CREDENTIALS,
scope analytics.readonly) pour obtenir les dimensions pays/date/page/
device necessaires -- sans toucher a Apps Script ni a la table existante.

Produit 4 rapports :
  1. Sessions par pays (30 derniers jours) -- situer le poids de la Chine.
  2. Sessions par jour pour la Chine (30 jours) -- detecter un volume
     anormalement constant (signature de bot) vs une vraie variabilite.
  3. Comportement Chine vs France sur les memes metriques (bounceRate,
     duree moyenne de session, pages vues/session) -- un bot authentique
     montre un bounceRate ~100% et une duree ~0s, contrairement a un vrai
     visiteur.
  4. Top pages visitees par les sessions Chine + repartition appareil/OS --
     un scraping de contenu cible plutot des pages precises de maniere
     repetitive et plus souvent via un seul type d'appareil/navigateur.

USAGE : python3 diagnostiquer_trafic_chine_ga4.py [--jours=30]
"""
import json
import os
import sys

try:
    import requests
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request as GoogleAuthRequest
except ImportError as e:
    sys.exit(f"❌ Dependance manquante : {e}")

PROPERTY_ID = "528487832"
SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]
API_URL = f"https://analyticsdata.googleapis.com/v1beta/properties/{PROPERTY_ID}:runReport"


def get_token():
    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not key_path:
        sys.exit("❌ GOOGLE_APPLICATION_CREDENTIALS manquant dans l'environnement")
    creds = service_account.Credentials.from_service_account_file(key_path, scopes=SCOPES)
    creds.refresh(GoogleAuthRequest())
    return creds.token


def run_report(token, dimensions, metrics, start_date, end_date, dimension_filter=None, limit=50):
    payload = {
        "dateRanges": [{"startDate": start_date, "endDate": end_date}],
        "dimensions": [{"name": d} for d in dimensions],
        "metrics": [{"name": m} for m in metrics],
        "limit": limit,
        "orderBys": [{"metric": {"metricName": metrics[0]}, "desc": True}],
    }
    if dimension_filter:
        payload["dimensionFilter"] = dimension_filter
    resp = requests.post(API_URL, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=30)
    if resp.status_code != 200:
        print(f"  ⚠️ Erreur API GA4 {resp.status_code} : {resp.text[:300]}")
        return []
    data = resp.json()
    rows = data.get("rows", [])
    out = []
    for r in rows:
        dims = [dv.get("value", "") for dv in r.get("dimensionValues", [])]
        mets = [mv.get("value", "") for mv in r.get("metricValues", [])]
        out.append(dims + mets)
    return out


def print_table(headers, rows):
    if not rows:
        print("  (aucune ligne)")
        return
    widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) for i, h in enumerate(headers)]
    print("  " + " | ".join(str(h).ljust(w) for h, w in zip(headers, widths)))
    for r in rows:
        print("  " + " | ".join(str(v).ljust(w) for v, w in zip(r, widths)))


def main():
    jours = 30
    for arg in sys.argv:
        if arg.startswith("--jours="):
            jours = int(arg.split("=", 1)[1])

    token = get_token()
    from datetime import date, timedelta
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=jours - 1)
    start_s, end_s = start.isoformat(), end.isoformat()
    print(f"🔎 Fenetre d'analyse : {start_s} -> {end_s} ({jours} jours)\n")

    print("=" * 70)
    print("1) SESSIONS PAR PAYS (top 15)")
    print("=" * 70)
    rows = run_report(token, ["country"], ["sessions", "bounceRate", "averageSessionDuration"], start_s, end_s, limit=15)
    print_table(["Pays", "Sessions", "BounceRate", "DureeMoyenneSec"], rows)

    print("\n" + "=" * 70)
    print("2) SESSIONS PAR JOUR -- CHINE")
    print("=" * 70)
    filtre_chine = {"filter": {"fieldName": "country", "stringFilter": {"value": "China"}}}
    rows = run_report(token, ["date"], ["sessions", "bounceRate", "averageSessionDuration"], start_s, end_s,
                       dimension_filter=filtre_chine, limit=jours + 5)
    rows.sort(key=lambda r: r[0])
    print_table(["Date", "Sessions", "BounceRate", "DureeMoyenneSec"], rows)

    print("\n" + "=" * 70)
    print("3) COMPARATIF CHINE VS FRANCE (memes metriques, meme fenetre)")
    print("=" * 70)
    for pays in ["China", "France"]:
        f = {"filter": {"fieldName": "country", "stringFilter": {"value": pays}}}
        rows = run_report(token, ["country"],
                           ["sessions", "bounceRate", "averageSessionDuration", "screenPageViews", "newUsers"],
                           start_s, end_s, dimension_filter=f, limit=1)
        print(f"  {pays} :")
        print_table(["Pays", "Sessions", "BounceRate", "DureeMoyenneSec", "PagesVues", "NouveauxUsers"], rows)

    print("\n" + "=" * 70)
    print("4a) TOP PAGES VISITEES -- CHINE")
    print("=" * 70)
    rows = run_report(token, ["pagePath"], ["sessions", "screenPageViews"], start_s, end_s,
                       dimension_filter=filtre_chine, limit=20)
    print_table(["Page", "Sessions", "PagesVues"], rows)

    print("\n" + "=" * 70)
    print("4b) APPAREIL / OS / NAVIGATEUR -- CHINE")
    print("=" * 70)
    rows = run_report(token, ["deviceCategory", "operatingSystem", "browser"], ["sessions"], start_s, end_s,
                       dimension_filter=filtre_chine, limit=20)
    print_table(["Appareil", "OS", "Navigateur", "Sessions"], rows)


if __name__ == "__main__":
    main()
