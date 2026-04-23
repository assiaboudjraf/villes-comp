"""
fetch_immobilier.py
--------------------
Télécharge les indicateurs immobiliers agrégés par commune.

Source  : data.gouv.fr - DVF agrégé par commune (Boris Méricskay)
Licence : Licence Ouverte / Open Licence version 2.0

Colonnes du fichier source :
  INSEE_COM, annee, nb_mutations, NbMaisons, NbApparts,
  PrixMoyen, Prixm2Moyen, SurfaceMoy
"""

import os
import requests
import pandas as pd

os.makedirs("data", exist_ok=True)

# ─── 1. URL via API data.gouv.fr (dynamique) ──────────────────────────────────
DATASET_ID = "indicateurs-immobiliers-par-commune-et-par-annee-prix-et-volumes-sur-la-periode-2014-2024"
API_URL    = f"https://www.data.gouv.fr/api/1/datasets/{DATASET_ID}/"

print("Récupération de l'URL du dataset DVF agrégé...")
download_url = None
try:
    r_meta = requests.get(API_URL, timeout=30)
    r_meta.raise_for_status()
    ressources = r_meta.json().get("resources", [])
    for res in ressources:
        if res.get("format", "").lower() == "csv" and res.get("url"):
            download_url = res["url"]
            break
    if not download_url and ressources:
        download_url = ressources[0]["url"]
    print(f"   ✓ URL : {str(download_url)[:80]}...")
except Exception as e:
    print(f"   ⚠️  API inaccessible ({e}) → URL de secours")
    download_url = "https://www.data.gouv.fr/fr/datasets/r/0ab442c5-57d1-4139-92dd-cc6de21ae0f9"

# ─── 2. Téléchargement ────────────────────────────────────────────────────────
print("Téléchargement...")
r = requests.get(download_url, timeout=120)
r.raise_for_status()
with open("data/immobilier_raw.csv", "wb") as f:
    f.write(r.content)
print("   ✓ Sauvegardé.")

# ─── 3. Chargement ────────────────────────────────────────────────────────────
df = pd.read_csv("data/immobilier_raw.csv", low_memory=False, dtype={"INSEE_COM": str})
print(f"   Colonnes : {list(df.columns)}")
print(f"   Lignes   : {len(df)}")

# ─── 4. Dernière année disponible ─────────────────────────────────────────────
if "annee" in df.columns:
    df["annee"] = pd.to_numeric(df["annee"], errors="coerce")
    annee_max = int(df["annee"].max())
    df = df[df["annee"] == annee_max].copy()
    print(f"   Année retenue : {annee_max}")

# ─── 5. Standardisation des colonnes ──────────────────────────────────────────
# Mapping des noms du fichier source vers les noms utilisés dans l'app
rename = {
    "INSEE_COM":   "code_insee",
    "NbApparts":   "nb_ventes_appart",
    "NbMaisons":   "nb_ventes_maison",
    "nb_mutations":"nb_ventes_total",
    "Prixm2Moyen": "prix_m2_appart",   # prix moyen toutes catégories — on l'utilise comme proxy
}
df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

# Ajouter prix_m2_maison si absent (on duplique prix_m2_appart en attendant mieux)
if "prix_m2_appart" in df.columns and "prix_m2_maison" not in df.columns:
    df["prix_m2_maison"] = df["prix_m2_appart"]

# ─── 6. Sélection finale ──────────────────────────────────────────────────────
colonnes_finales = ["code_insee", "annee", "prix_m2_appart", "prix_m2_maison",
                    "nb_ventes_appart", "nb_ventes_maison", "nb_ventes_total"]
colonnes_presentes = [c for c in colonnes_finales if c in df.columns]
df_final = df[colonnes_presentes].copy()

if "code_insee" in df_final.columns:
    df_final["code_insee"] = df_final["code_insee"].astype(str).str.zfill(5)
    df_final = df_final.dropna(subset=["code_insee"])

df_final.to_csv("data/immobilier.csv", index=False, encoding="utf-8")
print(f"\n✅ data/immobilier.csv → {len(df_final)} communes")
print(df_final.head(5).to_string())
