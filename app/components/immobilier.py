"""
components/immobilier.py
-------------------------
Source : DVF agrégé par commune (data.gouv.fr / Boris Méricskay)
Colonnes réelles du fichier :
  code_insee, annee, prix_m2_appart (=Prixm2Moyen), prix_m2_maison (idem),
  nb_ventes_appart (NbApparts), nb_ventes_maison (NbMaisons), nb_ventes_total (nb_mutations)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import load_immobilier, COULEUR_V1, COULEUR_V2


def _get_immo(df: pd.DataFrame, code_insee: str) -> dict:
    if df.empty:
        return {}
    # Essayer avec et sans zfill
    for code in [code_insee, str(code_insee).zfill(5)]:
        row = df[df["code_insee"].astype(str).str.zfill(5) == str(code).zfill(5)]
        if not row.empty:
            return row.iloc[0].to_dict()
    return {}


def afficher_section_immobilier(ville1: dict, ville2: dict):
    st.header("Logement & Immobilier")

    df_immo = load_immobilier()

    if df_immo.empty:
        st.error("❌ Fichier data/immobilier.csv introuvable. Relancez python scripts/fetch_immobilier.py")
        return

    immo1 = _get_immo(df_immo, str(ville1.get("code_insee", "")))
    immo2 = _get_immo(df_immo, str(ville2.get("code_insee", "")))

    # ── Métriques côte à côte ──────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    donnees = []

    for col, ville, immo, couleur in [
        (col1, ville1, immo1, COULEUR_V1),
        (col2, ville2, immo2, COULEUR_V2),
    ]:
        with col:
            nom = ville.get("nom_standard", "—")
            st.markdown(f"<h4 style='color:{couleur};'>{nom}</h4>", unsafe_allow_html=True)

            if not immo:
                st.warning(f"Données immobilières non disponibles pour {nom}.")
                donnees.append(None)
                continue

            annee = immo.get("annee", "—")
            st.caption(f"Source : DVF agrégé — année {annee}")

            prix_m2   = immo.get("prix_m2_appart") or immo.get("prix_m2_maison")
            nb_appart = immo.get("nb_ventes_appart")
            nb_maison = immo.get("nb_ventes_maison")
            nb_total  = immo.get("nb_ventes_total")

            def fmt_prix(v):
                try:
                    return f"{float(v):,.0f} €/m²".replace(",", " ") if v and pd.notna(v) else "—"
                except Exception:
                    return "—"

            def fmt_nb(v):
                try:
                    return f"{int(float(v))}" if v and pd.notna(v) else "—"
                except Exception:
                    return "—"

            m1, m2 = st.columns(2)
            m1.metric("Prix moyen au m²", fmt_prix(prix_m2))
            m2.metric("Ventes totales",   fmt_nb(nb_total))
            m1.metric("Ventes appartements", fmt_nb(nb_appart))
            m2.metric("Ventes maisons",      fmt_nb(nb_maison))
            donnees.append(immo)

    # ── Graphique comparatif ───────────────────────────────────────────────────
    st.divider()

    immo_ok = [(ville1, immo1, COULEUR_V1), (ville2, immo2, COULEUR_V2)]
    immo_ok = [(v, i, c) for v, i, c in immo_ok if i]

    if len(immo_ok) >= 1:
        # Bar chart prix au m²
        noms  = [v.get("nom_standard","—") for v,i,c in immo_ok]
        prix  = []
        for _, i, _ in immo_ok:
            p = i.get("prix_m2_appart") or i.get("prix_m2_maison")
            try:
                prix.append(float(p) if p and pd.notna(p) else 0)
            except Exception:
                prix.append(0)
        couleurs = [c for _,_,c in immo_ok]

        fig = go.Figure(go.Bar(
            x=noms, y=prix,
            marker_color=couleurs,
            text=[f"{p:,.0f} €/m²".replace(",", " ") for p in prix],
            textposition="outside",
        ))
        fig.update_layout(
            title="Prix moyen au m² (toutes transactions 2024)",
            yaxis_title="€ / m²",
            height=380,
            margin=dict(l=40, r=20, t=60, b=40),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Volume des ventes
        nb1 = immo1.get("nb_ventes_total", 0) if immo1 else 0
        nb2 = immo2.get("nb_ventes_total", 0) if immo2 else 0

        if nb1 or nb2:
            fig2 = go.Figure()
            categories = ["Appartements", "Maisons", "Total"]
            for ville, immo, couleur in [(ville1, immo1, COULEUR_V1), (ville2, immo2, COULEUR_V2)]:
                if not immo:
                    continue
                vals = []
                for key in ["nb_ventes_appart", "nb_ventes_maison", "nb_ventes_total"]:
                    try:
                        v = immo.get(key)
                        vals.append(int(float(v)) if v and pd.notna(v) else 0)
                    except Exception:
                        vals.append(0)
                fig2.add_trace(go.Bar(
                    name=ville.get("nom_standard","—"),
                    x=categories, y=vals,
                    marker_color=couleur, opacity=0.8,
                ))
            fig2.update_layout(
                barmode="group",
                title="Volume de transactions (2024)",
                yaxis_title="Nombre de ventes",
                height=350,
                legend=dict(orientation="h", y=1.1),
                margin=dict(l=40, r=20, t=60, b=40),
            )
            st.plotly_chart(fig2, use_container_width=True)

    st.caption(
        "Source : Indicateurs DVF agrégés par commune, Boris Méricskay / data.gouv.fr. "
        "Dérivé des Demandes de Valeurs Foncières (DGFiP). Licence Ouverte v2.0."
    )
