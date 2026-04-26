"""
fetch_all.py - Lance tous les scripts de collecte dans l'ordre.
"""
import subprocess, sys, os

script_dir   = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
os.chdir(project_root)

scripts = [
    ("1/4 — Villes françaises +20 000 hab",         "scripts/fetch_villes.py"),
    ("2/4 — Prix immobilier (DVF agrégé)",            "scripts/fetch_immobilier.py"),
    ("3/4 — Taux de chômage (fichiers INSEE locaux)", "scripts/fetch_chomage.py"),
    ("4/4 — Tourismes dans chaque ville (fichiers INSEE locaux)", "scripts/fetch_tourisme.py")
]

print("=" * 60)
print("  COLLECTE DES DONNÉES — Comparateur de Villes")
print("=" * 60)

errors = []
for label, script in scripts:
    print(f"\n▶  {label}")
    print("-" * 60)
    result = subprocess.run([sys.executable, script])
    if result.returncode != 0:
        errors.append(script)
        print(f"❌ Erreur dans {script}")
    else:
        print(f"✓  Terminé")

print("\n" + "=" * 60)
if errors:
    print(f"⚠️  {len(errors)} script(s) ont échoué : {errors}")
else:
    print("✅ Toutes les données sont prêtes !")
    print("   Lance : python -m streamlit run app/app.py")
print("=" * 60)
