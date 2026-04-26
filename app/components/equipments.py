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

# ───────────────────────────────────────────────
# ENDPOINTS OVERPASS
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

# ───────────────────────────────────────────────
# NOUVELLE PALETTE (8 couleurs)
# ───────────────────────────────────────────────
PALETTE_EQ = [
    "#cc4c02",
    "#225ea8",
    "#238443",
    "#7a0177",
    "#df65b0",
    "#969696",
    "#7fcdbb",
    "#b2182b",
]

CATEGORIES_EQ = [
    "Cinémas",
    "Musées",
    "Bibliothèques",
    "Théâtres",
    "Stades",
    "Piscines",
    "Hôpitaux",
    "Établissements d'enseignement supérieur ",
]

COULEURS_EQ = {cat: PALETTE_EQ[i] for i, cat in enumerate(CATEGORIES_EQ)}





# ───────────────────────────────────────────────
# OVERPASS QUERY
# ───────────────────────────────────────────────

def overpass_query(query: str):
    for url in ENDPOINTS:
        try:
            r = requests.post(url, data={"data": query}, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return None


# ───────────────────────────────────────────────
# RÉCUPÉRATION DES ÉQUIPEMENTS
# ───────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_equipements(lat: float, lon: float, rayon_m: int = 5000):

    categories = {
        "Cinémas":                                  ('cinema',       'amenity'),
        "Musées":                                   ('museum',       'tourism'),
        "Bibliothèques":                            ('library',      'amenity'),
        "Théâtres":                                 ('theatre',      'amenity'),
        "Stades":                                   ('stadium',      'leisure'),
        "Piscines":                                 ('swimming_pool','leisure'),
        "Hôpitaux":                                 ('hospital',     'amenity'),
        "Établissements d'enseignement supérieur ": ('university',   'amenity'),
    }

    resultats = {}
    points = []

    for label, (value, key) in categories.items():

        query = f"""
        [out:json][timeout:20];
        (
            node["{key}"="{value}"](around:{rayon_m},{lat},{lon});
            way["{key}"="{value}"](around:{rayon_m},{lat},{lon});
        );
        out center tags;
        """

        data = overpass_query(query)
        elems = data.get("elements", []) if data else []
        resultats[label] = len(elems)

        for e in elems:

            # Coordonnées
            if "lat" in e and "lon" in e:
                lat_e, lon_e = e["lat"], e["lon"]
            elif "center" in e:
                lat_e, lon_e = e["center"]["lat"], e["center"]["lon"]
            else:
                continue

            tags = e.get("tags", {})
            nom = tags.get("name", "Établissement")

            # Infos détaillées
            info_parts = []
            for k in [
                "addr:housenumber", "addr:street", "addr:postcode", "addr:city",
                "phone", "contact:phone", "website", "opening_hours", "email"
            ]:
                if k in tags:
                    info_parts.append(f"{k}: {tags[k]}")

            info = "<br>".join(info_parts) if info_parts else "Aucune information"

            points.append({
                "category": label,
                "name": nom,
                "info": info,
                "lat": lat_e,
                "lon": lon_e,
                "color": COULEURS_EQ[label],
            })

    return resultats, points


# ───────────────────────────────────────────────
# CARTE PYDECK AVEC TOOLTIP COMPLET
# ───────────────────────────────────────────────

def carte_pydeck(points, lat, lon):
    df = pd.DataFrame(points)

    # Convertir hex → RGB
    df["color_rgb"] = df["color"].apply(
    lambda c: [int(c[i:i+2], 16) for i in (1, 3, 5)]
)


    layer = pdk.Layer(
    "ScatterplotLayer",
    data=df,
    get_position='[lon, lat]',
    get_color='color_rgb',
    get_radius=150,
    pickable=True,
)


    view_state = pdk.ViewState(latitude=lat, longitude=lon, zoom=11, pitch=0)

    return pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_provider="carto",
        map_style="light",
        tooltip={
            "html": "<b>{category}</b><br>{name}<br><br>{info}",
            "style": {"backgroundColor": "white", "color": "black"},
        },
    )


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

    # Cartes
    st.subheader("Cartes interactives des villes")
    colA, colB = st.columns(2)

    with colA:
        st.markdown(f"### {ville1['nom_standard']}")
        st.pydeck_chart(carte_pydeck(pts1, lat1, lon1), height=400)

    with colB:
        st.markdown(f"### {ville2['nom_standard']}")
        st.pydeck_chart(carte_pydeck(pts2, lat2, lon2), height=400)

    # Légende
    st.divider()
    st.markdown("### Légende des couleurs")
    cols_leg = st.columns(4)

    for i, cat in enumerate(CATEGORIES_EQ):
        couleur = COULEURS_EQ[cat]
        cols_leg[i % 4].markdown(
            f"""
            <div style="display:flex;align-items:center;margin-bottom:6px;">
                <span style="
                    display:inline-block;width:14px;height:14px;border-radius:50%;
                    background:{couleur};margin-right:8px;">
                </span>
                <span>{cat}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()

    # Décompte (labels en noir)
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"<h4 style='color:{COULEUR_V1};'>{ville1['nom_standard']}</h4>", unsafe_allow_html=True)
        for label, val in eq1.items():
            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;padding:4px 0;">
                    <span style="font-weight:500;color:#111;">{label}</span>
                    <span style="font-weight:600;">{val}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

    with col2:
        st.markdown(f"<h4 style='color:{COULEUR_V2};'>{ville2['nom_standard']}</h4>", unsafe_allow_html=True)
        for label, val in eq2.items():
            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;padding:4px 0;">
                    <span style="font-weight:500;color:#111;">{label}</span>
                    <span style="font-weight:600;">{val}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

    # Graphique comparatif
    st.divider()
    categories = list(eq1.keys())

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=ville1["nom_standard"],
        x=categories,
        y=[eq1[c] for c in categories],
        marker_color=COULEUR_V1,
        opacity=0.85,
    ))
    fig.add_trace(go.Bar(
        name=ville2["nom_standard"],
        x=categories,
        y=[eq2[c] for c in categories],
        marker_color=COULEUR_V2,
        opacity=0.85,
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

    st.plotly_chart(fig, use_container_width=True)
