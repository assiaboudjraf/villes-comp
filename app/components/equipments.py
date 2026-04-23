"""
components/equipements.py
"""

import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd
import folium
from streamlit_folium import st_folium
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import COULEUR_V1, COULEUR_V2


# ───────────────────────────────────────────────
# ENDPOINTS OVERPASS AVEC FALLBACK
# ───────────────────────────────────────────────
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass-api.nl/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter"
]

HEADERS = {
    "User-Agent": "VilleComparer/1.0 (contact: test@example.com)",
    "Accept": "application/json"
}


def overpass_query(query: str):
    for url in ENDPOINTS:
        try:
            r = requests.post(url, data={"data": query}, headers=HEADERS, timeout=8)
            if r.status_code == 200:
                return r.json()
        except:
            pass
    return None


# ───────────────────────────────────────────────
# RÉCUPÉRATION DES ÉQUIPEMENTS
# ───────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_equipements(lat: float, lon: float, rayon_m: int = 5000):
    categories = {
        "Cinémas":      ('cinema',      'amenity', "purple"),
        "Musées":       ('museum',      'tourism', "green"),
        "Bibliothèques": ('library',     'amenity', "orange"),
        "Théâtres":     ('theatre',     'amenity', "yellow"),
        "Stades":        ('stadium',     'leisure', "blue"),
        "Piscines":     ('swimming_pool','leisure', "cadetblue"),
        "Hôpitaux":     ('hospital',    'amenity', "red"),
        "Universités":  ('university',  'amenity', "pink")
    }

    resultats = {}
    points = []

    for label, (value, key, color) in categories.items():
        query = f"""
        [out:json][timeout:15];
        node["{key}"="{value}"](around:{rayon_m},{lat},{lon});
        out body;
        """

        data = overpass_query(query)

        if data and "elements" in data:
            elems = data["elements"]
            resultats[label] = len(elems)

            for e in elems:
                if "lat" in e and "lon" in e:
                    points.append({
                        "category": label,
                        "lat": e["lat"],
                        "lon": e["lon"],
                        "color": color
                    })
        else:
            resultats[label] = 0

    return resultats, points


# ───────────────────────────────────────────────
# CARTE FOLIUM (VILLE UNIQUE)
# ───────────────────────────────────────────────
def carte_folium(points, lat, lon):
    m = folium.Map(location=[lat, lon], zoom_start=12, tiles="OpenStreetMap")

    for p in points:
        folium.CircleMarker(
            location=[p["lat"], p["lon"]],
            radius=6,
            color=p["color"],
            fill=True,
            fill_opacity=0.8,
            popup=p["category"]
        ).add_to(m)

    return m


# ───────────────────────────────────────────────
# AFFICHAGE STREAMLIT
# ───────────────────────────────────────────────
def afficher_section_equipements(ville1: dict, ville2: dict):
    st.header("Équipements & Services")

    lat1, lon1 = ville1["latitude"], ville1["longitude"]
    lat2, lon2 = ville2["latitude"], ville2["longitude"]

    with st.spinner("Chargement des équipements (OpenStreetMap)…"):
        eq1, pts1 = get_equipements(lat1, lon1)
        eq2, pts2 = get_equipements(lat2, lon2)

    # ─────────── 2 CARTES CÔTE À CÔTÉ ───────────
    st.subheader("Cartes interactives des villes")

    colA, colB = st.columns(2)

    with colA:
        st.markdown(f"### 🔵 {ville1['nom_standard']}")
        m1 = carte_folium(pts1, lat1, lon1)
        st_folium(m1, width=500, height=400)

    with colB:
        st.markdown(f"### 🔴 {ville2['nom_standard']}")
        m2 = carte_folium(pts2, lat2, lon2)
        st_folium(m2, width=500, height=400)

    # ─────────── LÉGENDE ───────────
    st.markdown("""
### Légende des couleurs
- 🟣 Cinémas  
- 🟢 Musées  
- 🟠 Bibliothèques  
- 🟡 Théâtres  
- 🔵 Stades  
- 🟦 Piscines  
- 🟥 Hôpitaux  
- 🌸 Universités  
""")

    # ─────────── Métriques ───────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"<h4 style='color:{COULEUR_V1};'>{ville1['nom_standard']}</h4>", unsafe_allow_html=True)
        for label, val in eq1.items():
            st.metric(label, val)

    with col2:
        st.markdown(f"<h4 style='color:{COULEUR_V2};'>{ville2['nom_standard']}</h4>", unsafe_allow_html=True)
        for label, val in eq2.items():
            st.metric(label, val)

    # ─────────── Graphique ───────────
    st.divider()
    categories = list(eq1.keys())
    vals1 = [eq1[c] for c in categories]
    vals2 = [eq2[c] for c in categories]

    fig = go.Figure()
    fig.add_trace(go.Bar(name=ville1["nom_standard"], x=categories, y=vals1, marker_color=COULEUR_V1))
    fig.add_trace(go.Bar(name=ville2["nom_standard"], x=categories, y=vals2, marker_color=COULEUR_V2))

    fig.update_layout(
        barmode="group",
        title="Comparaison des équipements (rayon 5 km)",
        yaxis_title="Nombre d'équipements",
        height=420,
        xaxis_tickangle=-20,
    )

    st.plotly_chart(fig, use_container_width=True)
