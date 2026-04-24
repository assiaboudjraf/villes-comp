"""
fetch_tourisme.py
------------------
Télécharge les hébergements touristiques classés par commune.

Source 1 : data.gouv.fr — "Hébergements touristiques classés en France"
           Liste des hôtels, campings, résidences, villages vacances, auberges
           Licence : Licence Ouverte v2.0

Source 2 : INSEE — "Capacité des communes en hébergement touristique"
           Nombre d'hôtels, chambres, campings, emplacements par commune
           Licence : Licence Ouverte v2.0
"""

import os
import requests
import pandas as pd

os.makedirs("data", exist_ok=True)

# ─── Source 1 : Hébergements classés (data.gouv.fr) ──────────────────────────
print("📥 Récupération des hébergements classés (data.gouv.fr)...")
DATASET_ID = "hebergements-collectifs-classes-en-france"
API_URL    = f"https://www.data.gouv.fr/api/1/datasets/{DATASET_ID}/"

download_url = None
try:
    r = requests.get(API_URL, timeout=30)
    r.raise_for_status()
    ressources = r.json().get("resources", [])
    # Chercher le CSV principal
    for res in ressources:
        if res.get("format", "").lower() == "csv":
            download_url = res["url"]
            break
    if not download_url and ressources:
        download_url = ressources[0]["url"]
    print(f"   ✓ URL : {str(download_url)[:80]}...")
except Exception as e:
    print(f"   ⚠️  API inaccessible : {e}")

if download_url:
    try:
        r2 = requests.get(download_url, timeout=120)
        r2.raise_for_status()
        with open("data/hebergements_raw.csv", "wb") as f:
            f.write(r2.content)
        print("   ✓ Fichier téléchargé.")

        # Chargement
        df_heb = pd.read_csv("data/hebergements_raw.csv", sep=";", dtype=str,
                             encoding="utf-8", on_bad_lines="skip", low_memory=False)
        # Essai latin-1 si UTF-8 échoue
        if len(df_heb.columns) <= 2:
            df_heb = pd.read_csv("data/hebergements_raw.csv", sep=";", dtype=str,
                                 encoding="latin-1", on_bad_lines="skip", low_memory=False)

        print(f"   Colonnes : {list(df_heb.columns[:8])}")
        print(f"   Lignes   : {len(df_heb)}")

        # Standardisation colonnes
        col_map = {}
        for c in df_heb.columns:
            cl = c.lower()
            if any(k in cl for k in ["commune_code", "code_insee", "code commune", "insee"]):
                col_map[c] = "code_insee"
            elif any(k in cl for k in ["type", "categorie", "mode"]):
                col_map[c] = "type_hebergement"
            elif any(k in cl for k in ["classement", "etoile", "catégorie", "nb_etoile"]):
                col_map[c] = "classement"
            elif any(k in cl for k in ["chambre", "nb_chambre"]):
                col_map[c] = "nb_chambres"
            elif any(k in cl for k in ["capacite", "place", "lit"]):
                col_map[c] = "capacite"
            elif any(k in cl for k in ["nom", "name", "etablissement"]):
                col_map[c] = "nom_etablissement"

        df_heb = df_heb.rename(columns=col_map)

        if "code_insee" in df_heb.columns:
            df_heb["code_insee"] = df_heb["code_insee"].astype(str).str.zfill(5)

            # Agrégation par commune et type
            agg_cols = {"nom_etablissement": "count"} if "nom_etablissement" in df_heb.columns else {}
            if "nb_chambres" in df_heb.columns:
                df_heb["nb_chambres"] = pd.to_numeric(df_heb["nb_chambres"], errors="coerce")
                agg_cols["nb_chambres"] = "sum"

            if "type_hebergement" in df_heb.columns:
                # Pivot : une ligne par commune, une colonne par type
                df_pivot = df_heb.groupby(["code_insee", "type_hebergement"]).size().unstack(fill_value=0)
                df_pivot.columns = [f"nb_{c.lower().replace(' ','_')[:20]}" for c in df_pivot.columns]
                df_pivot = df_pivot.reset_index()
                df_pivot["total_hebergements"] = df_pivot.drop("code_insee", axis=1).sum(axis=1)
            else:
                df_pivot = df_heb.groupby("code_insee").size().reset_index(name="total_hebergements")

            # Capacité totale si disponible
            if "capacite" in df_heb.columns:
                df_heb["capacite"] = pd.to_numeric(df_heb["capacite"], errors="coerce")
                cap = df_heb.groupby("code_insee")["capacite"].sum().reset_index(name="capacite_totale")
                df_pivot = df_pivot.merge(cap, on="code_insee", how="left")

            df_pivot.to_csv("data/tourisme.csv", index=False, encoding="utf-8")
            print(f"\n✅ data/tourisme.csv → {len(df_pivot)} communes")
            print(df_pivot.head(5).to_string())
        else:
            print("   ⚠️  Colonne code_insee non trouvée — sauvegarde du fichier brut tel quel.")
            df_heb.to_csv("data/tourisme.csv", index=False, encoding="utf-8")

    except Exception as e:
        print(f"   ❌ Erreur téléchargement : {e}")
        # Fichier vide de secours
        pd.DataFrame(columns=["code_insee","total_hebergements","capacite_totale"]).to_csv(
            "data/tourisme.csv", index=False)
else:
    print("   ❌ Aucune URL trouvée — fichier vide de secours.")
    pd.DataFrame(columns=["code_insee","total_hebergements","capacite_totale"]).to_csv(
        "data/tourisme.csv", index=False)
