"""
fetch_tourisme.py
------------------
Lit data/hebergements_classes.csv et produit data/tourisme.csv
Source : data.gouv.fr — Hébergements touristiques classés en France
Licence : Licence Ouverte v2.0
"""

import os
import re
import unicodedata
import pandas as pd

os.makedirs("data", exist_ok=True)

PATH = "data/hebergements_classes.csv"

if not os.path.exists(PATH):
    print(f"❌ Fichier manquant : {PATH}")
    exit(1)

# ─── 1. Chargement ────────────────────────────────────────────────────────────
print("📂 Lecture du fichier hébergements classés...")
df = None
for sep in ["\t", ";", ","]:
    for enc in ["latin-1", "utf-8", "utf-8-sig", "cp1252"]:
        try:
            tmp = pd.read_csv(PATH, sep=sep, dtype=str, encoding=enc, on_bad_lines="skip")
            if len(tmp.columns) > 5:
                df = tmp
                print(f"   ✓ sep='{sep}' encoding='{enc}' — {len(df)} lignes, {len(df.columns)} colonnes")
                break
        except Exception:
            continue
    if df is not None:
        break

if df is None:
    print("❌ Impossible de lire le fichier.")
    exit(1)

print(f"   Colonnes brutes : {list(df.columns)}")

# ─── 2. Nettoyage des noms de colonnes ───────────────────────────────────────
def clean_colname(s):
    """Normalise un nom de colonne en ASCII pur sans accents."""
    s = str(s).strip()
    # Normalisation Unicode NFD puis suppression des diacritiques
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    # Minuscules, espaces → underscore, caractères spéciaux supprimés
    s = s.lower()
    s = re.sub(r"[\s\(\)/'-]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

df.columns = [clean_colname(c) for c in df.columns]
print(f"   Colonnes nettoyées : {list(df.columns)}")

# ─── 3. Détection des colonnes clés ──────────────────────────────────────────
def find_col(df, *keywords):
    for kw in keywords:
        for c in df.columns:
            if kw.lower() in c.lower():
                return c
    return None

col_commune  = find_col(df, "commune")
col_cp       = find_col(df, "postal", "cp")
col_type     = find_col(df, "typolog", "type")
col_capacite = find_col(df, "capacit", "accueil")
col_chambres = find_col(df, "chambre")

print(f"   commune='{col_commune}' cp='{col_cp}' type='{col_type}' capacite='{col_capacite}'")

# ─── 4. Normalisation commune ─────────────────────────────────────────────────
if col_commune:
    df[col_commune] = df[col_commune].astype(str).str.upper().str.strip()
if col_cp:
    df[col_cp] = df[col_cp].astype(str).str.zfill(5)

# ─── 5. Nettoyage des valeurs de type hébergement ────────────────────────────
if col_type:
    def clean_type(s):
        s = str(s).strip()
        s = unicodedata.normalize("NFD", s)
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        return s.upper().strip()
    df[col_type] = df[col_type].apply(clean_type)
    print(f"   Types trouvés : {df[col_type].unique()[:8]}")

# ─── 6. Jointure avec villes_20000 ───────────────────────────────────────────
path_villes = "data/villes_20000.csv"
if not os.path.exists(path_villes):
    print("❌ data/villes_20000.csv manquant.")
    exit(1)

df_villes = pd.read_csv(path_villes, dtype={"code_insee": str, "code_postal": str})
df_villes["nom_upper"]   = df_villes["nom_standard"].astype(str).str.upper().str.strip()
df_villes["code_postal"] = df_villes["code_postal"].astype(str).str.zfill(5)

df["nom_upper"] = df[col_commune].astype(str) if col_commune else ""
df["cp5"]       = df[col_cp].astype(str).str[:5] if col_cp else ""

# Jointure nom + CP
df_join = df.merge(
    df_villes[["code_insee", "nom_upper", "code_postal"]],
    left_on=["nom_upper", "cp5"],
    right_on=["nom_upper", "code_postal"],
    how="left"
)
# Fallback nom seul
mask = df_join["code_insee"].isna()
if mask.sum() > 0:
    fb = df[mask].merge(
        df_villes[["code_insee", "nom_upper"]].drop_duplicates("nom_upper"),
        on="nom_upper", how="left"
    )
    df_join.loc[mask, "code_insee"] = fb["code_insee"].values

matched = df_join["code_insee"].notna().sum()
print(f"   ✓ {matched}/{len(df_join)} hébergements matchés ({matched/len(df_join)*100:.1f}%)")

df_matched = df_join[df_join["code_insee"].notna()].copy()

# ─── 7. Agrégation par commune ────────────────────────────────────────────────
if col_type:
    # Noms propres pour les colonnes pivot
    type_map = {
        "HOTEL DE TOURISME":          "hotels",
        "CAMPING":                     "campings",
        "RESIDENCE DE TOURISME":       "residences",
        "VILLAGE DE VACANCES":         "villages_vacances",
        "AUBERGE COLLECTIVE":          "auberges",
        "PARC RESIDENTIEL DE LOISIRS": "parcs_loisirs",
    }
    df_matched["type_clean"] = df_matched[col_type].map(
        lambda x: type_map.get(x, re.sub(r"[^a-z0-9]", "_", x.lower())[:20])
    )
    pivot = df_matched.groupby(["code_insee", "type_clean"]).size().unstack(fill_value=0)
    pivot.columns = [f"nb_{c}" for c in pivot.columns]
    pivot = pivot.reset_index()
    pivot["total_hebergements"] = pivot.drop("code_insee", axis=1).sum(axis=1)
else:
    pivot = df_matched.groupby("code_insee").size().reset_index(name="total_hebergements")

# Capacité
if col_capacite:
    df_matched[col_capacite] = pd.to_numeric(
        df_matched[col_capacite].astype(str).str.replace("-", "0"), errors="coerce"
    )
    cap = df_matched.groupby("code_insee")[col_capacite].sum().reset_index(name="capacite_totale")
    pivot = pivot.merge(cap, on="code_insee", how="left")

# Chambres
if col_chambres:
    df_matched[col_chambres] = pd.to_numeric(
        df_matched[col_chambres].astype(str).str.replace("-", "0"), errors="coerce"
    )
    chb = df_matched.groupby("code_insee")[col_chambres].sum().reset_index(name="nb_chambres_total")
    pivot = pivot.merge(chb, on="code_insee", how="left")

# ─── 8. Sauvegarde ────────────────────────────────────────────────────────────
pivot.to_csv("data/tourisme.csv", index=False, encoding="utf-8")
print(f"\n✅ data/tourisme.csv → {len(pivot)} communes")
print(f"   Colonnes : {list(pivot.columns)}")
print(pivot.head(5).to_string())
