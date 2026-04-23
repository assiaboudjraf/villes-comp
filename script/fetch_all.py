"""
fetch_all.py
-------------
Lance tous les scripts de collecte dans le bon ordre.

Fichiers INSEE à placer manuellement dans data/ avant de lancer :
  - data/chomage_raw.xlsx        (taux chômage zones emploi)
  - data/appartenance_communes.csv (correspondance commune → zone emploi)
"""

import subprocess
import sys
import os

script_dir   = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
os.chdir(project_root)

scripts = [
    ("1/3 — Villes françaises +20 000 hab (data.gouv.fr)",  "scripts/fetch_villes.py"),
    ("2/3 — Prix immobilier (DVF agrégé, data.gouv.fr)",    "scripts/fetch_immobilier.py"),
    ("3/3 — Taux de chômage (fichiers INSEE locaux)",        "scripts/fetch_chomage.py"),
]

print("=" * 60)
print("  COLLECTE DES DONNÉES — Comparateur de Villes")
print("=" * 60)

errors = []
for label, script_path in scripts:
    print(f"\n {label}")
    print("-" * 60)
    result = subprocess.run([sys.executable, script_path])
    if result.returncode != 0:
        errors.append(script_path)
        print(f"❌ Erreur dans {script_path}")
    else:
        print(f"✓  Terminé avec succès")

print("\n" + "=" * 60)
if errors:
    print(f"⚠️  {len(errors)} script(s) ont échoué : {errors}")
else:
    print("✅ Toutes les données sont prêtes !")
    print("   Lance : python -m streamlit run app/app.py")
print("=" * 60)
