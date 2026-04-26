"""
components/acp.py
------------------
Analyse Comparative sur l'ensemble des indicateurs disponibles.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import load_immobilier, load_chomage, COULEUR_V1, COULEUR_V2

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


def load_tourisme_acp() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "tourisme.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, dtype={"code_insee": str}, low_memory=False)


def construire_vecteur(ville: dict) -> dict:
    code = str(ville.get("code_insee", "")).zfill(5)
    vecteur = {}

    vecteur["Population (milliers)"] = float(ville.get("population", 0) or 0) / 1000
    vecteur["Densité (hab/km²)"]     = float(ville.get("densite", 0) or 0)
    vecteur["Superficie (km²)"]      = float(ville.get("superficie", 0) or 0)

    df_immo = load_immobilier()
    if not df_immo.empty and "code_insee" in df_immo.columns:
        row = df_immo[df_immo["code_insee"].astype(str).str.zfill(5) == code]
        if not row.empty:
            r = row.iloc[0]
            vecteur["Prix m² (€)"]         = float(r.get("prix_m2_appart", 0) or 0)
            vecteur["Ventes immobilières"]  = float(r.get("nb_ventes_total", 0) or 0)

    df_cho = load_chomage()
    if not df_cho.empty and "code_insee" in df_cho.columns:
        row = df_cho[df_cho["code_insee"].astype(str).str.zfill(5) == code]
        if not row.empty:
            vecteur["Taux chômage (%)"] = float(row.iloc[0].get("taux_chomage", 0) or 0)

    df_tour = load_tourisme_acp()
    if not df_tour.empty and "code_insee" in df_tour.columns:
        row = df_tour[df_tour["code_insee"].astype(str).str.zfill(5) == code]
        if not row.empty:
            r = row.iloc[0]
            vecteur["Hébergements classés"] = float(r.get("total_hebergements", 0) or 0)
            try:
                cap = r.get("capacite_totale", 0)
                if cap:
                    vecteur["Capacité touristique"] = float(cap)
            except Exception:
                pass

    return vecteur


def normaliser(v1: dict, v2: dict) -> tuple:
    indicateurs = list(v1.keys())
    vals1 = np.array([v1.get(k, 0) for k in indicateurs], dtype=float)
    vals2 = np.array([v2.get(k, 0) for k in indicateurs], dtype=float)
    max_vals = np.maximum(np.abs(vals1), np.abs(vals2))
    max_vals[max_vals == 0] = 1
    return indicateurs, vals1, vals2, vals1 / max_vals, vals2 / max_vals


def _radar(indicateurs, v1_norm, v2_norm, nom1, nom2):
    cats_c = indicateurs + [indicateurs[0]]
    v1_c   = list(v1_norm) + [v1_norm[0]]
    v2_c   = list(v2_norm) + [v2_norm[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=v1_c, theta=cats_c, fill="toself",
                                  name=nom1, line_color=COULEUR_V1,
                                  fillcolor=COULEUR_V1, opacity=0.35))
    fig.add_trace(go.Scatterpolar(r=v2_c, theta=cats_c, fill="toself",
                                  name=nom2, line_color=COULEUR_V2,
                                  fillcolor=COULEUR_V2, opacity=0.35))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="Profil comparatif normalisé",
        height=500,
        legend=dict(orientation="h", y=-0.15),
        margin=dict(l=60, r=60, t=80, b=60),
    )
    return fig


def _bars(indicateurs, vals1, vals2, nom1, nom2):
    fig = go.Figure()
    fig.add_trace(go.Bar(name=nom1, x=indicateurs, y=vals1,
                         marker_color=COULEUR_V1, opacity=0.85))
    fig.add_trace(go.Bar(name=nom2, x=indicateurs, y=vals2,
                         marker_color=COULEUR_V2, opacity=0.85))
    fig.update_layout(
        barmode="group",
        title="Comparaison des indicateurs (valeurs brutes)",
        height=450,
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=40, r=20, t=60, b=100),
        xaxis_tickangle=-30,
    )
    return fig


def _score(v1_norm, v2_norm, nom1, nom2):
    s1 = float(np.mean(v1_norm)) * 100
    s2 = float(np.mean(v2_norm)) * 100
    fig = go.Figure(go.Bar(
        x=[nom1, nom2], y=[s1, s2],
        marker_color=[COULEUR_V1, COULEUR_V2],
        text=[f"{s1:.1f}", f"{s2:.1f}"],
        textposition="outside",
        width=0.4,
    ))
    fig.update_layout(
        title="Score global comparatif",
        yaxis=dict(range=[0, 120], title="Score (0–100)"),
        height=380,
        margin=dict(l=40, r=20, t=60, b=40),
        showlegend=False,
    )
    return fig, s1, s2


def afficher_section_acp(ville1: dict, ville2: dict):
    st.header("Analyse Comparative")

# ── Calcul du score global pour TOUTES les villes ─────────────────────────────
from utils import load_villes

df_villes = load_villes()
scores_globaux = {}

for _, row in df_villes.iterrows():
    ville_tmp = row.to_dict()
    vect = construire_vecteur(ville_tmp)
    if vect:
        vals = np.array(list(vect.values()), dtype=float)
        max_vals = np.maximum(vals, 1)
        score = float(np.mean(vals / max_vals)) * 100
        scores_globaux[row["nom"]] = score

# ── Affichage du Top 10 national ─────────────────────────────────────────────
st.subheader("🏆 Top 10 des villes françaises (score global)")
afficher_top10(scores_globaux, nom1, nom2)
st.divider()



    nom1 = ville1.get("nom_standard", "Ville 1")
    nom2 = ville2.get("nom_standard", "Ville 2")

    # ── Explication méthodologique ────────────────────────────────────────────
    with st.expander("Comment fonctionne cette analyse ?", expanded=False):
        st.markdown("""
### Méthodologie

Cette section propose une **analyse comparative multidimensionnelle** des deux villes
sélectionnées, en s'appuyant sur l'ensemble des indicateurs collectés dans l'application.

#### Indicateurs utilisés
Les indicateurs proviennent de quatre sources :
- **Données générales** (INSEE) : population, densité, superficie
- **Immobilier** (DVF / data.gouv.fr) : prix moyen au m², volume de transactions
- **Emploi** (INSEE) : taux de chômage par zone d'emploi
- **Tourisme** (data.gouv.fr) : nombre d'hébergements classés, capacité d'accueil

#### Normalisation
Les indicateurs ont des unités très différentes (habitants, euros, pourcentages…).
Pour les rendre comparables, chaque valeur est **normalisée entre 0 et 1** :

```
valeur_normalisée = valeur / max(valeur_ville1, valeur_ville2)
```

La ville qui a la valeur la plus élevée obtient un score de 1, l'autre un score proportionnel.
Cela permet de comparer des grandeurs d'échelles très différentes sur un même graphique.

#### Score global
Le **score global** est la moyenne arithmétique de tous les indicateurs normalisés,
multipliée par 100 pour être exprimée sur une échelle de 0 à 100.

```
score = moyenne(indicateurs normalisés) × 100
```

> **Attention** : un score élevé signifie que la ville est supérieure à l'autre
> sur la **majorité** des indicateurs. Cela ne signifie pas qu'elle est
> "meilleure" dans l'absolu — certains indicateurs comme le taux de chômage
> sont à interpréter inversement (plus bas = mieux).

#### Radar normalisé
Le graphique radar montre le **profil comparatif** des deux villes sur chaque dimension.
Plus la surface colorée est grande, plus la ville domine sur l'ensemble des critères.

#### Limites
- Les données manquantes sont remplacées par 0, ce qui peut sous-estimer certaines villes.
- L'analyse est **relative** : elle compare uniquement les deux villes entre elles,
  pas par rapport à une moyenne nationale.
- Le score global donne un poids **égal** à chaque indicateur.
        """)

    st.divider()

    with st.spinner("Calcul des indicateurs..."):
        v1 = construire_vecteur(ville1)
        v2 = construire_vecteur(ville2)

    if not v1 or not v2:
        st.warning("Données insuffisantes pour l'analyse.")
        return

    indicateurs, vals1, vals2, v1_norm, v2_norm = normaliser(v1, v2)

    # ── Tableau ───────────────────────────────────────────────────────────────
    st.subheader("Tableau des indicateurs")
    df_table = pd.DataFrame({
        "Indicateur": indicateurs,
        nom1: [f"{v:,.1f}".replace(",", " ") for v in vals1],
        nom2: [f"{v:,.1f}".replace(",", " ") for v in vals2],
        f"Score {nom1} (normalisé)": [f"{v:.2f}" for v in v1_norm],
        f"Score {nom2} (normalisé)": [f"{v:.2f}" for v in v2_norm],
    })
    st.dataframe(df_table, hide_index=True, use_container_width=True)

    st.divider()

    # ── Score global ──────────────────────────────────────────────────────────
    st.subheader("Score global")
    st.caption(
        "Moyenne des indicateurs normalisés × 100. "
        "Un score de 100 signifie que la ville est supérieure à l'autre sur tous les critères."
    )
    fig_score, s1, s2 = _score(v1_norm, v2_norm, nom1, nom2)
    st.plotly_chart(fig_score, use_container_width=True)

    if s1 > s2:
        st.success(f"🏆 **{nom1}** obtient un score global supérieur ({s1:.1f} vs {s2:.1f})")
    elif s2 > s1:
        st.success(f"🏆 **{nom2}** obtient un score global supérieur ({s2:.1f} vs {s1:.1f})")
    else:
        st.info("Les deux villes obtiennent un score équivalent.")

    st.caption(
        "⚠️ Le score global agrège tous les indicateurs avec un poids égal. "
        "Il est à interpréter avec précaution : certains indicateurs comme le taux de chômage "
        "sont favorables quand ils sont **bas**, ce que le score ne reflète pas directement."
    )

    st.divider()

    # ── Graphiques ────────────────────────────────────────────────────────────
    tab1, tab2 = st.tabs(["Radar normalisé", "Barres comparatives"])
    with tab1:
        st.plotly_chart(_radar(indicateurs, v1_norm, v2_norm, nom1, nom2),
                        use_container_width=True)
        st.caption(
            "Valeurs normalisées entre 0 et 1 par rapport au maximum des deux villes. "
            "Plus la surface est grande, plus la ville domine sur l'ensemble des critères."
        )
    with tab2:
        st.plotly_chart(_bars(indicateurs, vals1, vals2, nom1, nom2),
                        use_container_width=True)
        st.caption("Valeurs brutes — les unités varient selon l'indicateur.")



