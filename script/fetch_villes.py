"""
fetch_villes.py
---------------
Source : data.gouv.fr "Communes et villes de France" + geo.api.gouv.fr pour les coords manquantes
"""

import os
import requests
import pandas as pd

os.makedirs("data", exist_ok=True)

# ─── 1. Téléchargement ────────────────────────────────────────────────────────
URL = "https://www.data.gouv.fr/fr/datasets/r/f5df602b-3800-44d7-b2df-fa40a0350325"
print("Téléchargement du fichier communes France...")
r = requests.get(URL, timeout=60)
r.raise_for_status()
with open("data/communes_france_raw.csv", "wb") as f:
    f.write(r.content)
print("   ✓ Sauvegardé.")

# ─── 2. Chargement ────────────────────────────────────────────────────────────
df = pd.read_csv("data/communes_france_raw.csv", dtype=str, low_memory=False)
df["population"] = pd.to_numeric(df["population"], errors="coerce")
print(f"   Total communes : {len(df)}")

# ─── 3. Filtrage +20 000 hab ──────────────────────────────────────────────────
df = df[df["population"] >= 20000].copy()
print(f"   Communes +20 000 hab : {len(df)}")

# ─── 4. Coordonnées GPS ───────────────────────────────────────────────────────
# Priorité : latitude_centre > latitude_mairie
for lat_col, lon_col in [("latitude_centre","longitude_centre"), ("latitude_mairie","longitude_mairie")]:
    if lat_col in df.columns and lon_col in df.columns:
        df["latitude"]  = pd.to_numeric(df[lat_col], errors="coerce")
        df["longitude"] = pd.to_numeric(df[lon_col], errors="coerce")
        print(f"   ✓ Coordonnées depuis : {lat_col} / {lon_col}")
        break

# Compléter les NaN via geo.api.gouv.fr
nan_mask = df["latitude"].isna() | df["longitude"].isna()
if nan_mask.sum() > 0:
    print(f"   {nan_mask.sum()} villes sans coordonnées → geo.api.gouv.fr...")
    r2 = requests.get(
        "https://geo.api.gouv.fr/communes",
        params={"fields": "code,centre", "format": "json", "limit": 5000},
        timeout=60
    )
    r2.raise_for_status()
    coords = {}
    for c in r2.json():
        cl = c.get("centre", {}).get("coordinates", [None, None])
        if cl[0] is not None:
            coords[c["code"]] = (cl[1], cl[0])  # (lat, lon)
    df.loc[nan_mask, "latitude"]  = df.loc[nan_mask, "code_insee"].map(lambda x: coords.get(x, (None,None))[0])
    df.loc[nan_mask, "longitude"] = df.loc[nan_mask, "code_insee"].map(lambda x: coords.get(x, (None,None))[1])
    print(f"   ✓ Coordonnées récupérées. NaN restants : {df['latitude'].isna().sum()}")

# ─── 5. Sélection et nettoyage ────────────────────────────────────────────────
colonnes = ["code_insee","nom_standard","dep_code","dep_nom","reg_nom",
            "code_postal","population","superficie_km2","densite","latitude","longitude"]
colonnes_ok = [c for c in colonnes if c in df.columns]
df = df[colonnes_ok].copy()
if "superficie_km2" in df.columns:
    df = df.rename(columns={"superficie_km2": "superficie"})
for col in ["population","superficie","densite","latitude","longitude"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=["nom_standard","latitude","longitude"])
df = df.sort_values("nom_standard").reset_index(drop=True)

# ─── 6. Sauvegarde ────────────────────────────────────────────────────────────
df.to_csv("data/villes_20000.csv", index=False, encoding="utf-8")
print(f"\n✅ data/villes_20000.csv → {len(df)} villes")
print(f"   NaN latitude : {df['latitude'].isna().sum()}")
print(df.head(5).to_string())
