"""
fetch_chomage.py
-----------------
Les deux fichiers INSEE ont 2 lignes d'en-tête :
  - Ligne 1 : labels lisibles (ignorée)
  - Ligne 2 : vrais noms de colonnes (CODGEO, ZE2020, LIBZE2020...)

appartenance_communes.csv : CODGEO;LIBGEO;DEP;...;ZE2020;...
chomage_raw.csv           : ZE2020;LIBZE2020;REG;LIBREG;2003-T1;...;2025-T4
"""

import os
import pandas as pd

os.makedirs("data", exist_ok=True)

def find_file(base):
    for ext in [".csv", ".xlsx"]:
        p = f"data/{base}{ext}"
        if os.path.exists(p):
            return p
    return None

PATH_CORR    = find_file("appartenance_communes")
PATH_CHOMAGE = find_file("chomage_raw")

manquants = []
if not PATH_CORR:    manquants.append("data/appartenance_communes.csv")
if not PATH_CHOMAGE: manquants.append("data/chomage_raw.csv")
if manquants:
    print("❌ Fichiers manquants :", manquants)
    exit(1)

print(f"✓ {PATH_CORR}")
print(f"✓ {PATH_CHOMAGE}")

# ─── 1. Table appartenance — header sur la ligne 2 (index 1) ─────────────────
print("\nLecture appartenance communes...")
df_corr = pd.read_csv(PATH_CORR, sep=";", header=1, dtype=str, encoding="utf-8-sig")
print(f"   Colonnes : {list(df_corr.columns[:6])}")
print(f"   Lignes   : {len(df_corr)}")

# Les vrais noms sont CODGEO et ZE2020
df_corr = df_corr.rename(columns={"CODGEO": "code_insee", "ZE2020": "code_ze"})
df_corr["code_insee"] = df_corr["code_insee"].astype(str).str.zfill(5)
df_corr["code_ze"]    = df_corr["code_ze"].astype(str).str.strip()
print(f"   ✓ code_insee et code_ze prêts")

# ─── 2. Taux chômage — header sur la ligne 2 (index 1) ───────────────────────
print("\nLecture chômage...")
df_cho = pd.read_csv(PATH_CHOMAGE, sep=";", header=1, dtype=str, encoding="utf-8-sig")
print(f"   Colonnes : {list(df_cho.columns[:6])}")
print(f"   Lignes   : {len(df_cho)}")

# Les vrais noms sont ZE2020 et LIBZE2020
df_cho = df_cho.rename(columns={"ZE2020": "code_ze", "LIBZE2020": "lib_ze"})
df_cho["code_ze"] = df_cho["code_ze"].astype(str).str.strip()

# Dernière colonne numérique = trimestre le plus récent (ex: 2025-T4)
cols_taux = []
for c in df_cho.columns:
    if c in ["code_ze", "lib_ze", "REG", "LIBREG"]:
        continue
    vals = pd.to_numeric(df_cho[c].astype(str).str.replace(",", "."), errors="coerce")
    if vals.notna().sum() > 50:
        cols_taux.append(c)

if cols_taux:
    derniere = cols_taux[-1]
    df_cho["taux_chomage"] = pd.to_numeric(
        df_cho[derniere].astype(str).str.replace(",", "."), errors="coerce"
    )
    print(f"   Taux utilisé : '{derniere}'")
else:
    print("   ⚠️  Aucun taux numérique trouvé")

# ─── 3. Jointure ──────────────────────────────────────────────────────────────
cols_cho  = [c for c in ["code_ze", "lib_ze", "taux_chomage"] if c in df_cho.columns]
df_merged = df_corr[["code_insee", "code_ze"]].merge(
    df_cho[cols_cho].drop_duplicates("code_ze"),
    on="code_ze", how="left"
)
print(f"\n   ✓ Jointure : {len(df_merged)} lignes")
print(f"   Taux non-nuls : {df_merged['taux_chomage'].notna().sum()}")

# ─── 4. Sauvegarde ────────────────────────────────────────────────────────────
df_merged.to_csv("data/chomage.csv", index=False, encoding="utf-8")
print(f"\n✅ data/chomage.csv → {len(df_merged)} lignes")
print(df_merged[df_merged["taux_chomage"].notna()].head(5).to_string())
