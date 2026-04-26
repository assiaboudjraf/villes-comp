"""
fetch_villes.py
---------------
Télécharge les communes françaises +20 000 habitants.
Gestion spéciale de Paris, Lyon et Marseille (communes à arrondissements).
"""

import os
import requests
import pandas as pd

os.makedirs("data", exist_ok=True)

# ─── Coordonnées fixes pour Paris, Lyon, Marseille ───────────────────────────
# Ces communes n'ont pas de coordonnées dans le CSV INSEE car elles sont
# découpées en arrondissements. On les renseigne manuellement.
COORDS_FIXES = {
    "75056": (48.8566,  2.3522),   # Paris
    "69123": (45.7640,  4.8357),   # Lyon
    "13055": (43.2965,  5.3698),   # Marseille
}

# ─── 1. Téléchargement ────────────────────────────────────────────────────────
URL = "https://www.data.gouv.fr/fr/datasets/r/f5df602b-3800-44d7-b2df-fa40a0350325"
print("📥 Téléchargement du fichier communes France...")
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
for lat_col, lon_col in [("latitude_centre", "longitude_centre"),
                          ("latitude_mairie", "longitude_mairie")]:
    if lat_col in df.columns and lon_col in df.columns:
        df["latitude"]  = pd.to_numeric(df[lat_col], errors="coerce")
        df["longitude"] = pd.to_numeric(df[lon_col], errors="coerce")
        print(f"   ✓ Coordonnées depuis : {lat_col} / {lon_col}")
        break

# Appliquer les coordonnées fixes pour Paris, Lyon, Marseille
for code, (lat, lon) in COORDS_FIXES.items():
    mask = df["code_insee"] == code
    if mask.any():
        df.loc[mask, "latitude"]  = lat
        df.loc[mask, "longitude"] = lon
        nom = df.loc[mask, "nom_standard"].values[0]
        print(f"   ✓ Coordonnées fixes appliquées : {nom} ({code})")

# Compléter les NaN restants via geo.api.gouv.fr
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
            coords[c["code"]] = (cl[1], cl[0])
    df.loc[nan_mask, "latitude"]  = df.loc[nan_mask, "code_insee"].map(
        lambda x: coords.get(x, (None, None))[0])
    df.loc[nan_mask, "longitude"] = df.loc[nan_mask, "code_insee"].map(
        lambda x: coords.get(x, (None, None))[1])
    print(f"   NaN restants : {df['latitude'].isna().sum()}")

# ─── 5. Sélection colonnes ────────────────────────────────────────────────────
colonnes = ["code_insee", "nom_standard", "dep_code", "dep_nom",
            "reg_nom", "code_postal", "population", "superficie_km2",
            "densite", "latitude", "longitude"]
colonnes_ok = [c for c in colonnes if c in df.columns]
df = df[colonnes_ok].copy()
if "superficie_km2" in df.columns:
    df = df.rename(columns={"superficie_km2": "superficie"})

for col in ["population", "superficie", "densite", "latitude", "longitude"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# ─── 6. Nettoyage ─────────────────────────────────────────────────────────────
# On ne supprime que les villes sans nom — on garde celles sans coords
# (on a traité Paris/Lyon/Marseille manuellement)
df = df.dropna(subset=["nom_standard", "latitude", "longitude"])
df = df.sort_values("nom_standard").reset_index(drop=True)

# ─── 7. Sauvegarde ────────────────────────────────────────────────────────────
df.to_csv("data/villes_20000.csv", index=False, encoding="utf-8")
print(f"\n✅ data/villes_20000.csv → {len(df)} villes")
print(f"   NaN latitude : {df['latitude'].isna().sum()}")

# Vérification Paris/Lyon/Marseille
for nom in ["Paris", "Lyon", "Marseille"]:
    row = df[df["nom_standard"] == nom]
    if not row.empty:
        r = row.iloc[0]
        print(f"   ✓ {nom} : lat={r['latitude']}, lon={r['longitude']}")
    else:
        print(f"   ⚠️  {nom} absent du fichier final")
