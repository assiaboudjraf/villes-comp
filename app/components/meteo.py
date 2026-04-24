"""
components/meteo.py
--------------------
Affiche prévisions 7j et climatologie mensuelle.
Source : Open-Meteo API (forecast + archive). Gratuit, sans clé. CC BY 4.0
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import get_meteo_previsions, get_meteo_historique, decode_wmo, COULEUR_V1, COULEUR_V2

MOIS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun", "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]


def _previsions_card(ville: dict, couleur: str):
    nom = ville.get("nom_standard", "—")
    lat = ville.get("latitude")
    lon = ville.get("longitude")

    st.markdown(f"<h4 style='color:{couleur};'>{nom}</h4>", unsafe_allow_html=True)

    if not lat or not lon or pd.isna(lat) or pd.isna(lon):
        st.warning("Coordonnées GPS manquantes pour cette ville.")
        return

    with st.spinner("Chargement météo..."):
        data = get_meteo_previsions(float(lat), float(lon))

    if "error" in data:
        st.error(f"Erreur API météo : {data['error']}")
        return

    daily  = data.get("daily", {})
    dates  = daily.get("time", [])
    t_max  = daily.get("temperature_2m_max", [])
    t_min  = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_sum", [])
    codes  = daily.get("weathercode", [])

    cols = st.columns(len(dates))
    for i, (col, date_str) in enumerate(zip(cols, dates)):
        with col:
            desc, emoji = decode_wmo(int(codes[i])) if i < len(codes) else ("—", "❓")
            tmax  = f"{t_max[i]:.0f}°"   if i < len(t_max)  else "—"
            tmin  = f"{t_min[i]:.0f}°"   if i < len(t_min)  else "—"
            pluie = f"{precip[i]:.1f}mm" if i < len(precip) else "—"
            try:
                d = pd.to_datetime(date_str)
                label = d.strftime("%a %d").capitalize()
            except Exception:
                label = date_str
            st.markdown(f"**{label}**  \n{emoji}  \n🌡️ {tmax}/{tmin}  \n💧 {pluie}")


def _build_climat_df(ville: dict):
    """Retourne un DataFrame avec temp_moy et precip_moy par mois (1-12)."""
    lat = ville.get("latitude")
    lon = ville.get("longitude")
    if not lat or not lon or pd.isna(lat) or pd.isna(lon):
        return None

    data = get_meteo_historique(float(lat), float(lon))
    if "error" in data:
        return None

    daily = data.get("daily", {})
    times = daily.get("time", [])
    temps = daily.get("temperature_2m_mean", [])
    precs = daily.get("precipitation_sum", [])

    if not times:
        return None

    df = pd.DataFrame({"date": times, "temp": temps, "precip": precs})
    df["date"]   = pd.to_datetime(df["date"])
    df["mois"]   = df["date"].dt.month
    df["temp"]   = pd.to_numeric(df["temp"],   errors="coerce")
    df["precip"] = pd.to_numeric(df["precip"], errors="coerce")

    result = df.groupby("mois").agg(
        temp_moy=("temp", "mean"),
        precip_moy=("precip", "mean")
    ).reindex(range(1, 13))
    return result


def _chart_temperature(ville1, ville2):
    fig = go.Figure()
    for ville, couleur in [(ville1, COULEUR_V1), (ville2, COULEUR_V2)]:
        df = _build_climat_df(ville)
        if df is None:
            continue
        fig.add_trace(go.Scatter(
            x=MOIS, y=df["temp_moy"].values,
            name=ville.get("nom_standard", "—"),
            line=dict(color=couleur, width=2.5),
            mode="lines+markers",
        ))
    fig.update_layout(
        title="Températures moyennes mensuelles",
        yaxis_title="°C", height=380,
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=40, r=20, t=60, b=40),
    )
    return fig


def _chart_precipitation(ville1, ville2):
    fig = go.Figure()
    for ville, couleur in [(ville1, COULEUR_V1), (ville2, COULEUR_V2)]:
        df = _build_climat_df(ville)
        if df is None:
            continue
        fig.add_trace(go.Bar(
            x=MOIS, y=df["precip_moy"].values,
            name=ville.get("nom_standard", "—"),
            marker_color=couleur, opacity=0.75,
        ))
    fig.update_layout(
        title="Précipitations moyennes mensuelles",
        yaxis_title="mm/jour", barmode="group", height=380,
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=40, r=20, t=60, b=40),
    )
    return fig


def afficher_section_meteo(ville1: dict, ville2: dict):
    st.header("Météo & Climat")

    st.subheader("Prévisions — 7 prochains jours")
    col1, col2 = st.columns(2)
    with col1:
        _previsions_card(ville1, COULEUR_V1)
    with col2:
        _previsions_card(ville2, COULEUR_V2)

    st.divider()
    annee_fin   = date.today().year - 1
    annee_debut = annee_fin - 4
    st.subheader(f"Climatologie (moyennes {annee_debut}–{annee_fin})")
    st.caption("Source : Open-Meteo Historical Weather API (ERA5) — données journalières agrégées par mois.")

    tab_temp, tab_precip = st.tabs(["🌡️ Températures", "💧 Précipitations"])
    with tab_temp:
        with st.spinner("Chargement climatologie..."):
            fig = _chart_temperature(ville1, ville2)
        st.plotly_chart(fig, use_container_width=True)
    with tab_precip:
        with st.spinner("Chargement climatologie..."):
            fig = _chart_precipitation(ville1, ville2)
        st.plotly_chart(fig, use_container_width=True)
