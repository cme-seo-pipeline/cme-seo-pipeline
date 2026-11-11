"""
CME — Diagnostic (lecture seule) de l'echec apparent de l'installation de
fonts-liberation sur le runner GitHub Actions, constate le 11/11/2026 :
le workflow a ajoute `sudo apt-get update -qq && sudo apt-get install -y
-qq fonts-liberation` avant le script, mais fc-list ne montre toujours
aucune police Liberation Sans juste apres -- alors que le log de ce
step ne montre qu'un warning DNS sur security.ubuntu.com, sans erreur
claire sur l'etape install elle-meme (silence total avec -qq, ambigu).

Ce script tourne APRES les memes etapes (donc dans le meme etat que le
script cible), et affiche en clair : accessibilite reseau des miroirs
apt, etat de dpkg pour le paquet, presence reelle des fichiers, et un
apt-get install -y (SANS -qq, pour voir le vrai message) relance ici
pour diagnostic.

LECTURE SEULE pour WordPress/BigQuery -- utilise sudo/apt uniquement
pour diagnostiquer l'etat du systeme (pas d'ecriture applicative).
"""
import subprocess
import os


def run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"


def main():
    print("1/ Etat dpkg du paquet fonts-liberation :")
    code, out, err = run("dpkg -l fonts-liberation 2>&1")
    print(f"   code={code}\n{out}\n{err}")

    print("\n2/ Fichiers reellement presents (find) :")
    code, out, err = run("find / -iname '*liberation*' 2>/dev/null | head -20")
    print(out or "(aucun fichier trouve)")

    print("\n3/ Accessibilite reseau des miroirs apt (ping DNS + HTTP) :")
    for host in ["security.ubuntu.com", "archive.ubuntu.com", "azure.archive.ubuntu.com", "packages.microsoft.com"]:
        code, out, err = run(f"getent hosts {host} 2>&1", timeout=10)
        resolu = "OK" if code == 0 else "ECHEC DNS"
        print(f"   {host:<28} resolution DNS -> {resolu} ({out.splitlines()[0] if out else err})")

    print("\n4/ Sources apt configurees :")
    code, out, err = run("cat /etc/apt/sources.list 2>/dev/null; cat /etc/apt/sources.list.d/*.sources 2>/dev/null; cat /etc/apt/sources.list.d/*.list 2>/dev/null")
    print(out[:2000] if out else "(vide ou illisible)")

    print("\n5/ Relance apt-get update + install SANS -qq (pour voir le vrai message) :")
    code, out, err = run("sudo apt-get update 2>&1 | tail -30", timeout=180)
    print(f"   update -> code={code}\n{out}")
    code, out, err = run("sudo apt-get install -y fonts-liberation 2>&1 | tail -40", timeout=120)
    print(f"   install -> code={code}\n{out}")

    print("\n6/ fc-list apres cette relance :")
    code, out, err = run("fc-list | grep -i liberation")
    print(out or "(toujours aucune police Liberation trouvee)")


if __name__ == "__main__":
    main()
