"""
components/tourisme.py
-----------------------
Analyse touristique combinant deux sources :
  1. Hébergements classés par commune (data.gouv.fr — Licence Ouverte v2.0)
  2. Points d'intérêt touristiques via API Overpass/OpenStreetMap (ODbL)

Graphiques : jauge capacité, donut types hébergements, scatter attractivité, carte POI
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import COULEUR_V1, COULEUR_V2

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

ENDPOINTS_OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass-api.nl/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

HEADERS = {"User-Agent": "ComparateurVilles/1.0", "Accept": "application/json"}


# ─── Chargement données hébergements ─────────────────────────────────────────

@st.cache_data
def load_tourisme() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "tourisme.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, dtype={"code_insee": str}, low_memory=False)


def get_tourisme_ville(df: pd.DataFrame, code_insee: str) -> dict:
    if df.empty or "code_insee" not in df.columns:
        return {}
    row = df[df["code_insee"].astype(str).str.zfill(5) == str(code_insee).zfill(5)]
    return row.iloc[0].to_dict() if not row.empty else {}


# ─── API Overpass : points d'intérêt touristiques ────────────────────────────

def overpass_query(query: str):
    for url in ENDPOINTS_OVERPASS:
        try:
            r = requests.post(url, data={"data": query}, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                return r.json()
        except Exception:
            continue
    return None


@st.cache_data(ttl=86400)
def get_poi_touristiques(lat: float, lon: float, rayon_m: int = 8000) -> dict:
    """
    Récupère les points d'intérêt touristiques via Overpass.
    Retourne un dict {catégorie: nombre}.
    """
COULEURS_POI = {
    "Hôtels":           "#2563EB",
    "Campings":         "#16A34A",
    "Attractions":      "#DC2626",
    "Galeries":         "#9333EA",
    "Offices tourisme": "#EA580C",
    "Restaurants":      "#CA8A04",
    "Cafés":            "#0891B2",
    "Commerces":        "#DB2777",
}

requetes = {
    "Hôtels":           f'node["tourism"="hotel"](around:{rayon_m},{lat},{lon});',
    "Campings":         f'node["tourism"="camp_site"](around:{rayon_m},{lat},{lon});',
    "Attractions":      f'node["tourism"="attraction"](around:{rayon_m},{lat},{lon});'
                      + f'way["tourism"="attraction"](around:{rayon_m},{lat},{lon});',
    "Galeries":         f'node["tourism"="gallery"](around:{rayon_m},{lat},{lon});',
    "Offices tourisme": f'node["tourism"="information"]["information"="office"](around:{rayon_m},{lat},{lon});',
    "Restaurants":      f'node["amenity"="restaurant"](around:{rayon_m},{lat},{lon});',
    "Cafés":            f'node["amenity"="cafe"](around:{rayon_m},{lat},{lon});',
    "Commerces":        f'node["shop"="gift"](around:{rayon_m},{lat},{lon});'
                      + f'node["shop"="souvenirs"](around:{rayon_m},{lat},{lon});',
}

resultats = {}
for label, filtre in requetes.items():
  query = f"[out:json][timeout:20];\n({filtre});\nout ids;"
  data  = overpass_query(query)
  resultats[label] = len(data.get("elements", [])) if data else 0
  return resultats


# ─── Graphiques ───────────────────────────────────────────────────────────────

def _gauge_hebergements(total: int, nom: str, couleur: str, max_val: int = 500) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=total,
        title={"text": f"Hébergements classés<br><b>{nom}</b>", "font": {"size": 13}},
        gauge={
            "axis": {"range": [0, max_val]},
            "bar":  {"color": couleur},
            "steps": [
                {"range": [0,    max_val*0.33], "color": "#FEE2E2"},
                {"range": [max_val*0.33, max_val*0.66], "color": "#FEF3C7"},
                {"range": [max_val*0.66, max_val],      "color": "#D1FAE5"},
            ],
        },
    ))
    fig.update_layout(height=260, margin=dict(l=20, r=20, t=60, b=20))
    return fig


def _donut_types(tour_dict: dict, nom: str, couleur: str) -> go.Figure:
    """Donut des types d'hébergements si les colonnes existent."""
    types_labels = []
    types_vals   = []
    prefixes = ["nb_h", "nb_c", "nb_r", "nb_v", "nb_a", "nb_m"]  # hôtel, camping, résidence...
    noms_lisibles = {
        "nb_h": "Hôtels", "nb_c": "Campings",
        "nb_r": "Résidences", "nb_v": "Villages vacances",
        "nb_a": "Auberges", "nb_m": "Meublés",
    }
    for k, v in tour_dict.items():
        if k.startswith("nb_") and k != "total_hebergements":
            try:
                val = float(v)
                if val > 0:
                    # Nom lisible
                    prefix = next((p for p in prefixes if k.startswith(p)), k)
                    label  = noms_lisibles.get(prefix, k.replace("nb_","").replace("_"," ").title())
                    types_labels.append(label)
                    types_vals.append(val)
            except Exception:
                pass

    if not types_vals:
        return None

    fig = go.Figure(go.Pie(
        labels=types_labels,
        values=types_vals,
        hole=0.5,
        marker_colors=px.colors.qualitative.Set2,
        textinfo="label+percent",
    ))
    fig.update_layout(
        title=f"Types d'hébergements — {nom}",
        height=320,
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=False,
    )
    return fig


def _bar_poi(poi1: dict, poi2: dict, nom1: str, nom2: str) -> go.Figure:
    categories = list(poi1.keys())
    vals1 = [poi1.get(c, 0) for c in categories]
    vals2 = [poi2.get(c, 0) for c in categories]

    fig = go.Figure()
    fig.add_trace(go.Bar(name=nom1, x=categories, y=vals1,
                         marker_color=COULEUR_V1, opacity=0.85))
    fig.add_trace(go.Bar(name=nom2, x=categories, y=vals2,
                         marker_color=COULEUR_V2, opacity=0.85))
    fig.update_layout(
        barmode="group",
        title="Points d'intérêt touristiques (rayon 8km, OpenStreetMap)",
        yaxis_title="Nombre",
        height=420,
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=40, r=20, t=60, b=80),
        xaxis_tickangle=-20,
    )
    return fig


def _radar_tourisme(poi1: dict, poi2: dict, nom1: str, nom2: str) -> go.Figure:
    categories = list(poi1.keys())
    vals1 = [poi1.get(c, 0) for c in categories]
    vals2 = [poi2.get(c, 0) for c in categories]
    # Fermer le radar
    categories_closed = categories + [categories[0]]
    vals1_closed = vals1 + [vals1[0]]
    vals2_closed = vals2 + [vals2[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals1_closed, theta=categories_closed,
        fill="toself", name=nom1,
        line_color=COULEUR_V1, fillcolor=COULEUR_V1,
        opacity=0.4,
    ))
    fig.add_trace(go.Scatterpolar(
        r=vals2_closed, theta=categories_closed,
        fill="toself", name=nom2,
        line_color=COULEUR_V2, fillcolor=COULEUR_V2,
        opacity=0.4,
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        title="Profil touristique comparatif",
        height=420,
        legend=dict(orientation="h", y=-0.1),
        margin=dict(l=40, r=40, t=60, b=60),
    )
    return fig


# ─── Point d'entrée ──────────────────────────────────────────────────────────

def afficher_section_tourisme(ville1: dict, ville2: dict):
    st.header("Tourisme & Attractivité")

    nom1 = ville1.get("nom_standard", "Ville 1")
    nom2 = ville2.get("nom_standard", "Ville 2")

    # ── Partie 1 : Hébergements classés (données statiques) ──────────────────
    st.subheader("Hébergements touristiques classés")
    st.caption("Source : data.gouv.fr — hébergements classés (hôtels, campings, résidences…). Licence Ouverte v2.0.")

    df_tour = load_tourisme()
    tour1   = get_tourisme_ville(df_tour, str(ville1.get("code_insee","")))
    tour2   = get_tourisme_ville(df_tour, str(ville2.get("code_insee","")))

    col1, col2 = st.columns(2)

    totaux = []
    for col, nom, tour, couleur in [(col1,nom1,tour1,COULEUR_V1),(col2,nom2,tour2,COULEUR_V2)]:
        with col:
            st.markdown(f"<h4 style='color:{couleur};'>{nom}</h4>", unsafe_allow_html=True)
            if not tour:
                st.info("Données hébergements non disponibles pour cette commune.")
                totaux.append(0)
                continue

            total = tour.get("total_hebergements", 0)
            try:
                total = int(float(total))
            except Exception:
                total = 0
            totaux.append(total)

            capacite = tour.get("capacite_totale")
            m1, m2 = st.columns(2)
            m1.metric("Hébergements classés", total)
            if capacite:
                try:
                    m2.metric("Capacité totale (lits/places)", f"{int(float(capacite)):,}".replace(",", " "))
                except Exception:
                    pass

            # Donut types si disponible
            fig_donut = _donut_types(tour, nom, couleur)
            if fig_donut:
                st.plotly_chart(fig_donut, use_container_width=True)

    # Jauges comparatives
    if any(t > 0 for t in totaux):
        max_val = max(max(totaux) * 1.3, 10)
        g1, g2 = st.columns(2)
        with g1:
            if totaux[0] > 0:
                st.plotly_chart(_gauge_hebergements(totaux[0], nom1, COULEUR_V1, int(max_val)),
                                use_container_width=True)
        with g2:
            if totaux[1] > 0:
                st.plotly_chart(_gauge_hebergements(totaux[1], nom2, COULEUR_V2, int(max_val)),
                                use_container_width=True)

    # ── Partie 2 : POI via OpenStreetMap ─────────────────────────────────────
    st.divider()
    st.subheader("📍 Points d'intérêt (OpenStreetMap)")
    st.caption("Source : API Overpass / OpenStreetMap — rayon 8km. Licence ODbL.")

    lat1, lon1 = ville1.get("latitude"), ville1.get("longitude")
    lat2, lon2 = ville2.get("latitude"), ville2.get("longitude")

    if not all([lat1, lon1, lat2, lon2]):
        st.warning("Coordonnées manquantes pour l'une des villes.")
        return

    with st.spinner("Chargement des points d'intérêt (OpenStreetMap)... ~20s"):
        poi1 = get_poi_touristiques(float(lat1), float(lon1))
        poi2 = get_poi_touristiques(float(lat2), float(lon2))

    # Métriques rapides
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"<h4 style='color:{COULEUR_V1};'>{nom1}</h4>", unsafe_allow_html=True)
        cols = st.columns(2)
        for i,(k,v) in enumerate(poi1.items()):
            cols[i%2].metric(k, v)
    with col2:
        st.markdown(f"<h4 style='color:{COULEUR_V2};'>{nom2}</h4>", unsafe_allow_html=True)
        cols = st.columns(2)
        for i,(k,v) in enumerate(poi2.items()):
            cols[i%2].metric(k, v)

    st.divider()

    # Graphiques côte à côte
    tab1, tab2 = st.tabs(["Barres comparatives", "Radar touristique"])
    with tab1:
        st.plotly_chart(_bar_poi(poi1, poi2, nom1, nom2), use_container_width=True)
    with tab2:
        st.plotly_chart(_radar_tourisme(poi1, poi2, nom1, nom2), use_container_width=True)
