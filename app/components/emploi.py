"""
components/emploi.py
---------------------
Affiche les données d'emploi : taux de chômage par zone d'emploi,
comparaison avec la moyenne nationale.

Source : INSEE — Taux de chômage localisés par zone d'emploi
Licence : Licence Ouverte v2.0
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import load_chomage, COULEUR_V1, COULEUR_V2

# Taux de chômage national de référence (source : INSEE, T4 2024)
# Source : https://www.insee.fr/fr/statistiques/8351234
TAUX_NATIONAL = 7.3


def _get_chomage(df_cho: pd.DataFrame, code_insee: str) -> dict:
    """Retourne les données chômage pour un code INSEE."""
    if df_cho.empty or "code_insee" not in df_cho.columns:
        return {}
    row = df_cho[df_cho["code_insee"] == code_insee]
    if row.empty:
        return {}
    return row.iloc[0].to_dict()


def _gauge_chomage(taux: float, nom: str, couleur: str) -> go.Figure:
    """Jauge de taux de chômage."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=taux,
        delta={"reference": TAUX_NATIONAL, "suffix": "%", "valueformat": ".1f"},
        number={"suffix": "%", "valueformat": ".1f"},
        title={"text": nom, "font": {"size": 14}},
        gauge={
            "axis": {"range": [0, 20], "ticksuffix": "%"},
            "bar": {"color": couleur},
            "steps": [
                {"range": [0, 5], "color": "#D1FAE5"},
                {"range": [5, 10], "color": "#FEF3C7"},
                {"range": [10, 20], "color": "#FEE2E2"},
            ],
            "threshold": {
                "line": {"color": "black", "width": 2},
                "thickness": 0.75,
                "value": TAUX_NATIONAL,
            },
        },
    ))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def afficher_section_emploi(ville1: dict, ville2: dict):
    """Point d'entrée principal du composant emploi."""
    st.header("Emploi & Chômage")

    df_cho = load_chomage()
    cho1 = _get_chomage(df_cho, str(ville1.get("code_insee", "")))
    cho2 = _get_chomage(df_cho, str(ville2.get("code_insee", "")))

    st.info(
        f"Les taux de chômage sont calculés par **zone d'emploi** (INSEE). "
        f"Référence nationale : **{TAUX_NATIONAL}%** (T4 2024, source INSEE)."
    )

    col1, col2 = st.columns(2)

    for col, ville, cho, couleur in [
        (col1, ville1, cho1, COULEUR_V1),
        (col2, ville2, cho2, COULEUR_V2),
    ]:
        with col:
            nom = ville.get("nom_standard", "—")
            st.markdown(f"<h4 style='color:{couleur};'>{nom}</h4>", unsafe_allow_html=True)

            if not cho or "taux_chomage" not in cho or pd.isna(cho.get("taux_chomage")):
                st.warning("Taux de chômage non disponible pour cette ville/zone d'emploi.")
                continue

            taux = float(cho["taux_chomage"])
            ze = cho.get("lib_ze", cho.get("lib_ze_corr", "—"))

            st.metric(
                label=f"Taux de chômage — Zone d'emploi de {ze}",
                value=f"{taux:.1f}%",
                delta=f"{taux - TAUX_NATIONAL:+.1f}% vs national",
                delta_color="inverse"  # rouge si > national
            )

            fig = _gauge_chomage(taux, nom, couleur)
            st.plotly_chart(fig, use_container_width=True)

    # --- Tableau comparatif ---
    st.divider()
    st.subheader("Comparaison")

    t1 = float(cho1.get("taux_chomage", 0)) if cho1 and not pd.isna(cho1.get("taux_chomage", float("nan"))) else None
    t2 = float(cho2.get("taux_chomage", 0)) if cho2 and not pd.isna(cho2.get("taux_chomage", float("nan"))) else None

    if t1 and t2:
        data = {
            "Indicateur": ["Taux de chômage", "Écart vs national", "Zone d'emploi"],
            ville1.get("nom_standard", "Ville 1"): [
                f"{t1:.1f}%",
                f"{t1 - TAUX_NATIONAL:+.1f}%",
                cho1.get("lib_ze", "—"),
            ],
            ville2.get("nom_standard", "Ville 2"): [
                f"{t2:.1f}%",
                f"{t2 - TAUX_NATIONAL:+.1f}%",
                cho2.get("lib_ze", "—"),
            ],
        }
        st.dataframe(pd.DataFrame(data), hide_index=True, use_container_width=True)

    st.caption(
        "Source : INSEE — Taux de chômage localisés par zone d'emploi "
        "(https://www.insee.fr/fr/statistiques/1893230). Licence Ouverte v2.0."
    )
