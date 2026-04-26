"""
components/acp.py
Analyse Comparative sur l'ensemble des indicateurs disponibles.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import load_immobilier, load_chomage, load_villes, COULEUR_V1, COULEUR_V2

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


# ───────────────────────────────────────────────────────────────
# Chargement tourisme
# ───────────────────────────────────────────────────────────────
def load_tourisme_acp() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "tourisme.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, dtype={"code_insee": str}, low_memory=False)


# ───────────────────────────────────────────────────────────────
# Construction du vecteur d'indicateurs pour une ville
# ───────────────────────────────────────────────────────────────
def construire_vecteur(ville: dict) -> dict:
    code = str(ville.get("code_insee", "")).zfill(5)
    vecteur = {}

    vecteur["Population (milliers)"] = float(ville.get("population", 0) or 0) / 1000
    vecteur["Densité (hab/km²)"]     = float(ville.get("densite", 0) or 0)
    vecteur["Superficie (km²)"]      = float(ville.get("superficie", 0) or 0)

    df_immo = load_immobilier()
    if not df_immo.empty:
        row = df_immo[df_immo["code_insee"].astype(str).str.zfill(5) == code]
        if not row.empty:
            r = row.iloc[0]
            vecteur["Prix m² (€)"]         = float(r.get("prix_m2_appart", 0) or 0)
            vecteur["Ventes immobilières"] = float(r.get("nb_ventes_total", 0) or 0)

    df_cho = load_chomage()
    if not df_cho.empty:
        row = df_cho[df_cho["code_insee"].astype(str).str.zfill(5) == code]
        if not row.empty:
            vecteur["Taux chômage (%)"] = float(row.iloc[0].get("taux_chomage", 0) or 0)

    df_tour = load_tourisme_acp()
    if not df_tour.empty:
        row = df_tour[df_tour["code_insee"].astype(str).str.zfill(5) == code]
        if not row.empty:
            r = row.iloc[0]
            vecteur["Hébergements classés"] = float(r.get("total_hebergements", 0) or 0)
            cap = r.get("capacite_totale", 0)
            if cap:
                vecteur["Capacité touristique"] = float(cap)

    return vecteur


# ───────────────────────────────────────────────────────────────
# Normalisation
# ───────────────────────────────────────────────────────────────
def normaliser(v1: dict, v2: dict):
    indicateurs = list(v1.keys())
    vals1 = np.array([v1[k] for k in indicateurs], dtype=float)
    vals2 = np.array([v2[k] for k in indicateurs], dtype=float)
    max_vals = np.maximum(vals1, vals2)
    max_vals[max_vals == 0] = 1
    return indicateurs, vals1, vals2, vals1 / max_vals, vals2 / max_vals


# ───────────────────────────────────────────────────────────────
# Radar
# ───────────────────────────────────────────────────────────────
def _radar(indicateurs, v1_norm, v2_norm, nom1, nom2):
    cats_c = indicateurs + [indicateurs[0]]
    v1_c   = list(v1_norm) + [v1_norm[0]]
    v2_c   = list(v2_norm) + [v2_norm[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=v1_c, theta=cats_c, fill="toself",
        name=nom1, line_color=COULEUR_V1,
        fillcolor=COULEUR_V1, opacity=0.35
    ))
    fig.add_trace(go.Scatterpolar(
        r=v2_c, theta=cats_c, fill="toself",
        name=nom2, line_color=COULEUR_V2,
        fillcolor=COULEUR_V2, opacity=0.35
    ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="Profil comparatif normalisé",
        height=500,
        legend=dict(orientation="h", y=-0.15),
        margin=dict(l=60, r=60, t=80, b=60),
    )
    return fig


# ───────────────────────────────────────────────────────────────
# Barres brutes
# ───────────────────────────────────────────────────────────────
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


# ───────────────────────────────────────────────────────────────
# Score global
# ───────────────────────────────────────────────────────────────
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


# ───────────────────────────────────────────────────────────────
# Top 10 national
# ───────────────────────────────────────────────────────────────
def afficher_top10(scores, ville1, ville2):
    df = pd.DataFrame([
        {"ville": v, "score": s} for v, s in scores.items()
    ]).sort_values("score", ascending=False)

    top10 = df.head(10)

    couleurs = []
    for v in top10["ville"]:
        if v == ville1:
            couleurs.append(COULEUR_V1)
        elif v == ville2:
            couleurs.append(COULEUR_V2)
        else:
            couleurs.append("#cccccc")

    fig = go.Figure(go.Bar(
        x=top10["score"],
        y=top10["ville"],
        orientation="h",
        marker_color=couleurs,
        opacity=0.85
    ))

    fig.update_layout(
        title="Top 10 des villes françaises (score global)",
        xaxis_title="Score normalisé",
        yaxis_title="",
        height=450,
        margin=dict(l=60, r=20, t=60, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)


# ───────────────────────────────────────────────────────────────
# SECTION PRINCIPALE ACP
# ───────────────────────────────────────────────────────────────
def afficher_section_acp(ville1: dict, ville2: dict):
    st.header("Analyse Comparative")

    nom1 = ville1.get("nom_standard", "Ville 1")
    nom2 = ville2.get("nom_standard", "Ville 2")

    # ── Calcul du score global pour toutes les villes ─────────────
    df_villes = load_villes()
    scores_globaux = {}

    for _, row in df_villes.iterrows():
        ville_tmp = row.to_dict()
        vect = construire_vecteur(ville_tmp)
        if vect:
            vals = np.array(list(vect.values()), dtype=float)
            max_vals = np.maximum(vals, 1)
            score = float(np.mean(vals / max_vals)) * 100

            nom_ville = row.get("nom_standard", "Ville inconnue")
            scores_globaux[nom_ville] = score

    # ── Affichage du Top 10 ───────────────────────────────────────
    st.subheader("🏆 Top 10 des villes françaises (score global)")
    afficher_top10(scores_globaux, nom1, nom2)
    st.divider()

    # ── Explication méthodologique ────────────────────────────────
    with st.expander("Comment fonctionne cette analyse ?", expanded=False):
        st.markdown("""
### Méthodologie
Analyse comparative multidimensionnelle basée sur :
- Données générales (INSEE)
- Immobilier (DVF)
- Emploi (INSEE)
- Tourisme (data.gouv.fr)

Normalisation : valeur_normalisée = valeur / max(valeur_ville1, valeur_ville2)
Score global = moyenne des indicateurs normalisés × 100.
        """)

    # ── Calcul des indicateurs ─────────────────────────────────────
    with st.spinner("Calcul des indicateurs..."):
        v1 = construire_vecteur(ville1)
        v2 = construire_vecteur(ville2)

    if not v1 or not v2:
        st.warning("Données insuffisantes pour l'analyse.")
        return

    indicateurs, vals1, vals2, v1_norm, v2_norm = normaliser(v1, v2)

    # ── Tableau ───────────────────────────────────────────────────
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

    # ── Score global ──────────────────────────────────────────────
    st.subheader("Score global")
    fig_score, s1, s2 = _score(v1_norm, v2_norm, nom1, nom2)
    st.plotly_chart(fig_score, use_container_width=True)

    st.divider()

    # ── Graphiques ────────────────────────────────────────────────
    tab1, tab2 = st.tabs(["Radar normalisé", "Barres comparatives"])
    with tab1:
        st.plotly_chart(_radar(indicateurs, v1_norm, v2_norm, nom1, nom2),
                        use_container_width=True)
    with tab2:
        st.plotly_chart(_bars(indicateurs, vals1, vals2, nom1, nom2),
                        use_container_width=True)
