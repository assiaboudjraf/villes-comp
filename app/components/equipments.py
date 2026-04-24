"""
components/equipements.py
"""

import streamlit as st
import requests
import plotly.graph_objects as go
import pydeck as pdk
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import COULEUR_V1, COULEUR_V2


ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass-api.nl/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter"
]

HEADERS = {
    "User-Agent": "VilleComparer/1.0 (contact: test@example.com)",
    "Accept": "application/json"
}

COULEURS_EQ = {
    "Cinémas":              "#7B00C8",
    "Musées":               "#00B400",
    "Bibliothèques":        "#FF8C00",
    "Théâtres":             "#DAA520",
    "Stades":               "#0000B4",
    "Piscines":             "#00FFC8",
    "Hôpitaux":             "#B40000",
    "Établissements d'enseignement supérieur ": "#FF69B4",
}


def overpass_query(query: str):
    for url in ENDPOINTS:
        try:
            r = requests.post(url, data={"data": query}, headers=HEADERS, timeout=8)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return None


@st.cache_data(ttl=3600)
def get_equipements(lat: float, lon: float, rayon_m: int = 5000):
    categories = {
        "Cinémas":              ('cinema',       'amenity', [123, 0, 200]),
        "Musées":               ('museum',       'tourism', [0, 180, 0]),
        "Bibliothèques":        ('library',      'amenity', [255, 140, 0]),
        "Théâtres":             ('theatre',      'amenity', [255, 215, 0]),
        "Stades":               ('stadium',      'leisure', [0, 0, 180]),
        "Piscines":             ('swimming_pool','leisure', [0, 255, 200]),
        "Hôpitaux":             ('hospital',     'amenity', [180, 0, 0]),
        "Établissements d'enseignement supérieur ": ('university', 'amenity', [255, 105, 180]),
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


def carte_pydeck(points, lat, lon):
    df = pd.DataFrame(points)

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[lon, lat]',
        get_color='color',
        get_radius=150,
        pickable=True,
    )

    view_state = pdk.ViewState(
        latitude=lat,
        longitude=lon,
        zoom=11,
        pitch=0,
    )

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_provider="carto",
        map_style="light",
        tooltip={"text": "{category}"}
    )

    return deck


def afficher_section_equipements(ville1: dict, ville2: dict):
    st.header("Équipements & Services")

    lat1, lon1 = ville1["latitude"], ville1["longitude"]
    lat2, lon2 = ville2["latitude"], ville2["longitude"]

    with st.spinner("Chargement des équipements (OpenStreetMap)…"):
        eq1, pts1 = get_equipements(lat1, lon1)
        eq2, pts2 = get_equipements(lat2, lon2)

    # ── Cartes interactives ───────────────────────────────────────────────────
    st.subheader("Cartes interactives des villes")
    colA, colB = st.columns(2)

    with colA:
        st.markdown(f"### 🔵 {ville1['nom_standard']}")
        deck1 = carte_pydeck(pts1, lat1, lon1)
        st.pydeck_chart(deck1, width="stretch", height=400)

    with colB:
        st.markdown(f"### 🔴 {ville2['nom_standard']}")
        deck2 = carte_pydeck(pts2, lat2, lon2)
        st.pydeck_chart(deck2, width="stretch", height=400)

    # ── Légende couleurs ──────────────────────────────────────────────────────
    # ── Légende couleurs ──────────────────────────────────────────────────────
    st.divider()
    st.markdown("""
**Légende des couleurs**  
<span style="display:inline-block;width:12px;height:12px;background:#7B00C8;border-radius:3px;margin-right:6px;vertical-align:middle;"></span> Cinémas &nbsp;&nbsp;
<span style="display:inline-block;width:12px;height:12px;background:#00B400;border-radius:3px;margin-right:6px;vertical-align:middle;"></span> Musées &nbsp;&nbsp;
<span style="display:inline-block;width:12px;height:12px;background:#FF8C00;border-radius:3px;margin-right:6px;vertical-align:middle;"></span> Bibliothèques &nbsp;&nbsp;
<span style="display:inline-block;width:12px;height:12px;background:#DAA520;border-radius:3px;margin-right:6px;vertical-align:middle;"></span> Théâtres &nbsp;&nbsp;
<span style="display:inline-block;width:12px;height:12px;background:#0000B4;border-radius:3px;margin-right:6px;vertical-align:middle;"></span> Stades &nbsp;&nbsp;
<span style="display:inline-block;width:12px;height:12px;background:#00FFC8;border-radius:3px;margin-right:6px;vertical-align:middle;"></span> Piscines &nbsp;&nbsp;
<span style="display:inline-block;width:12px;height:12px;background:#B40000;border-radius:3px;margin-right:6px;vertical-align:middle;"></span> Hôpitaux &nbsp;&nbsp;
<span style="display:inline-block;width:12px;height:12px;background:#FF69B4;border-radius:3px;margin-right:6px;vertical-align:middle;"></span> Établissements d'enseignement supérieur
""", unsafe_allow_html=True)

    # ── Métriques avec labels colorés ─────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"<h4 style='color:{COULEUR_V1};'>{ville1['nom_standard']}</h4>",
                    unsafe_allow_html=True)
        cols = st.columns(2)
        for i, (label, val) in enumerate(eq1.items()):
            couleur = COULEURS_EQ.get(label, "#888")
            cols[i % 2].markdown(
                f'<span style="color:{couleur};font-weight:600;">{label}</span>',
                unsafe_allow_html=True)
            cols[i % 2].metric(label="", value=val)

    with col2:
        st.markdown(f"<h4 style='color:{COULEUR_V2};'>{ville2['nom_standard']}</h4>",
                    unsafe_allow_html=True)
        cols = st.columns(2)
        for i, (label, val) in enumerate(eq2.items()):
            couleur = COULEURS_EQ.get(label, "#888")
            cols[i % 2].markdown(
                f'<span style="color:{couleur};font-weight:600;">{label}</span>',
                unsafe_allow_html=True)
            cols[i % 2].metric(label="", value=val)

    # ── Graphique comparatif ──────────────────────────────────────────────────
    st.divider()
    categories = list(eq1.keys())
    vals1 = [eq1[c] for c in categories]
    vals2 = [eq2[c] for c in categories]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=ville1["nom_standard"], x=categories, y=vals1,
        marker_color=COULEUR_V1, opacity=0.85,
    ))
    fig.add_trace(go.Bar(
        name=ville2["nom_standard"], x=categories, y=vals2,
        marker_color=COULEUR_V2, opacity=0.85,
    ))
    fig.update_layout(
        barmode="group",
        title="Comparaison des équipements (rayon 5 km)",
        yaxis_title="Nombre d'équipements",
        height=420,
        xaxis_tickangle=-20,
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=40, r=20, t=60, b=80),
    )
    st.plotly_chart(fig, width="stretch")
