"""
components/tourisme.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import pydeck as pdk
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import COULEUR_V1, COULEUR_V2

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
)

ENDPOINTS_OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass-api.nl/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
HEADERS = {"User-Agent": "ComparateurVilles/1.0", "Accept": "application/json"}

PALETTE_POI = [
    "#cc4c02",  # Hôtels
    "#225ea8",  # Campings
    "#238443",  # Attractions
    "#7a0177",  # Galeries
    "#df65b0",  # Offices tourisme
    "#969696",  # Restaurants
    "#7fcdbb",  # Cafés
    "#b2182b",  # Commerces
]

COULEURS_POI = {
    "Hôtels": PALETTE_POI[0],
    "Campings": PALETTE_POI[1],
    "Attractions": PALETTE_POI[2],
    "Galeries": PALETTE_POI[3],
    "Offices tourisme": PALETTE_POI[4],
    "Restaurants": PALETTE_POI[5],
    "Cafés": PALETTE_POI[6],
    "Commerces": PALETTE_POI[7],
}

COULEURS_HEBERG = {
    "Hôtels": "#2563EB",
    "Campings": "#16A34A",
    "Résidences": "#CA8A04",
}

TYPES_LABELS = {
    "nb_hotels": "Hôtels",
    "nb_ha_tel_de_tourisme": "Hôtels",
    "nb_campings": "Campings",
    "nb_residences": "Résidences",
    "nb_ra_sidence_de_touris": "Résidences",
    "nb_villages_vacances": "Résidences",
    "nb_auberges": "Résidences",
    "nb_parcs_loisirs": "Résidences",
    "nb_parc_ra_sidentiel_de": "Résidences",
}


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
    if row.empty:
        return {}
    return row.iloc[0].to_dict()


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
def get_poi_touristiques(lat: float, lon: float, rayon_m: int = 8000):
    requetes = {
        "Hôtels": ("tourism", "hotel"),
        "Campings": ("tourism", "camp_site"),
        "Attractions": ("tourism", "attraction"),
        "Galeries": ("tourism", "gallery"),
        "Offices tourisme": ("tourism", "information"),
        "Restaurants": ("amenity", "restaurant"),
        "Cafés": ("amenity", "cafe"),
        "Commerces": ("shop", "gift"),
    }

    resultats = {}
    points = []

    for label, (key, value) in requetes.items():
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
            if "lat" in e and "lon" in e:
                lat_e, lon_e = e["lat"], e["lon"]
            elif "center" in e:
                lat_e, lon_e = e["center"]["lat"], e["center"]["lon"]
            else:
                continue

            tags = e.get("tags", {})
            nom = tags.get("name", "Établissement")

            info_parts = []
            for k in [
                "addr:housenumber",
                "addr:street",
                "addr:postcode",
                "addr:city",
                "phone",
                "contact:phone",
                "website",
                "opening_hours",
            ]:
                if k in tags:
                    info_parts.append(f"{k}: {tags[k]}")
            info = "<br>".join(info_parts) if info_parts else "Aucune information"

            points.append(
                {
                    "category": label,
                    "name": nom,
                    "info": info,
                    "lat": lat_e,
                    "lon": lon_e,
                    "color": COULEURS_POI.get(label, "#888"),
                }
            )

    return resultats, points


def carte_poi_tourisme(points, lat, lon):
    if not points:
        return None

    df = pd.DataFrame(points)
    df["color_rgb"] = df["color"].apply(
        lambda c: [int(c[i : i + 2], 16) for i in (1, 3, 5)]
    )

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position="[lon, lat]",
        get_color="color_rgb",
        get_radius=140,
        pickable=True,
    )

    view_state = pdk.ViewState(latitude=lat, longitude=lon, zoom=12, pitch=0)

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


def _legende_couleurs():
    st.markdown("**Légende des couleurs (POI)**")
    cols = st.columns(4)
    for i, (label, couleur) in enumerate(COULEURS_POI.items()):
        cols[i % 4].markdown(
            f'<div style="display:flex;align-items:center;margin-bottom:6px;">'
            f'<span style="display:inline-block;width:14px;height:14px;border-radius:50%;'
            f'background:{couleur};margin-right:8px;"></span><span>{label}</span></div>',
            unsafe_allow_html=True,
        )


def _legende_hebergements():
    st.markdown("### Légende des types d'hébergements")
    cols = st.columns(3)

    for i, (label, couleur) in enumerate(COULEURS_HEBERG.items()):
        html = (
            f"<div style='display:flex;align-items:center;margin-bottom:6px;'>"
            f"<span style='display:inline-block;width:14px;height:14px;border-radius:50%;"
            f"background:{couleur};margin-right:8px;'></span>"
            f"<span>{label}</span>"
            f"</div>"
        )
        cols[i].markdown(html, unsafe_allow_html=True)



def _gauge_hebergements(total, nom, couleur, max_val=500):
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=total,
            number={"font": {"size": 36, "color": "#111"}, "valueformat": "d"},
            title={
                "text": f"<b>Hébergements classés</b><br>{nom}",
                "font": {"size": 16, "color": "#444"},
            },
            domain={"x": [0, 1], "y": [0.30, 1]},
            gauge={
                "axis": {
                    "range": [0, max_val],
                    "tickwidth": 1,
                    "tickcolor": "#999",
                    "tickfont": {"size": 12},
                },
                "bar": {"color": couleur},
                "bgcolor": "white",
                "steps": [],
                "threshold": {
                    "line": {"color": "black", "width": 2},
                    "thickness": 0.8,
                    "value": max_val * 0.5,
                },
            },
        )
    )

    fig.update_layout(
        height=240,
        margin=dict(l=0, r=0, t=40, b=0),
    )

    return fig


def _donut_types(tour_dict, nom):
    labels, vals, seen = [], [], set()
    for col, label in TYPES_LABELS.items():
        if label in seen:
            continue
        try:
            v = float(tour_dict.get(col, 0))
            if v > 0:
                labels.append(label)
                vals.append(v)
                seen.add(label)
        except Exception:
            pass

    if not vals:
        return None

    colors = [COULEURS_HEBERG.get(l, "#888") for l in labels]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=vals,
            hole=0.5,
            marker=dict(colors=colors),
            textinfo="label+percent",
        )
    )
    fig.update_layout(
        title=f"Types d'hébergements — {nom}",
        height=320,
        showlegend=False,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig


def _bar_poi(poi1, poi2, nom1, nom2):
    categories = list(poi1.keys())
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name=nom1,
            x=categories,
            y=[poi1.get(c, 0) for c in categories],
            marker_color=COULEUR_V1,
            opacity=0.85,
        )
    )
    fig.add_trace(
        go.Bar(
            name=nom2,
            x=categories,
            y=[poi2.get(c, 0) for c in categories],
            marker_color=COULEUR_V2,
            opacity=0.85,
        )
    )
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


def _radar_tourisme(poi1, poi2, nom1, nom2):
    categories = list(poi1.keys())

    v1 = [poi1.get(c, 0) for c in categories]
    v2 = [poi2.get(c, 0) for c in categories]

    max_vals = [max(v1[i], v2[i], 1) for i in range(len(categories))]
    v1_norm = [v1[i] / max_vals[i] for i in range(len(categories))]
    v2_norm = [v2[i] / max_vals[i] for i in range(len(categories))]

    cats_c = categories + [categories[0]]
    v1_c = v1_norm + [v1_norm[0]]
    v2_c = v2_norm + [v2_norm[0]]

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=v1_c,
            theta=cats_c,
            fill="toself",
            name=f"{nom1} (normalisé)",
            line_color=COULEUR_V1,
            fillcolor=COULEUR_V1,
            opacity=0.4,
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=v2_c,
            theta=cats_c,
            fill="toself",
            name=f"{nom2} (normalisé)",
            line_color=COULEUR_V2,
            fillcolor=COULEUR_V2,
            opacity=0.4,
        )
    )

    fig.update_layout(
        title="Profil touristique comparatif (normalisé)",
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        height=420,
        legend=dict(orientation="h", y=-0.1),
        margin=dict(l=40, r=40, t=60, b=60),
    )

    return fig


def afficher_section_tourisme(ville1: dict, ville2: dict):
    st.header("Tourisme & Attractivité")

    nom1 = ville1.get("nom_standard", "Ville 1")
    nom2 = ville2.get("nom_standard", "Ville 2")

    st.subheader("Hébergements touristiques classés")
    st.caption("Source : data.gouv.fr — hébergements classés. Licence Ouverte v2.0.")

    df_tour = load_tourisme()
    tour1 = get_tourisme_ville(df_tour, str(ville1.get("code_insee", "")))
    tour2 = get_tourisme_ville(df_tour, str(ville2.get("code_insee", "")))

    col1, col2 = st.columns(2)
    totaux = []

    for col, nom, tour, couleur in [
        (col1, nom1, tour1, COULEUR_V1),
        (col2, nom2, tour2, COULEUR_V2),
    ]:
        with col:
            st.markdown(
                f"<h4 style='color:{couleur};'>{nom}</h4>", unsafe_allow_html=True
            )
            if not tour or "total_hebergements" not in tour:
                st.info("Données hébergements non disponibles.")
                totaux.append(0)
                continue

            total = int(float(tour.get("total_hebergements", 0)))
            capacite = tour.get("capacite_totale")
            chambres = tour.get("nb_chambres_total")
            totaux.append(total)

            m1, m2 = st.columns(2)
            m1.metric("Hébergements classés", total)
            if capacite:
                try:
                    m2.metric(
                        "Capacité",
                        f"{int(float(capacite)):,}".replace(",", " "),
                    )
                except Exception:
                    pass
            if chambres:
                try:
                    m1.metric(
                        "Nb de chambres",
                        f"{int(float(chambres)):,}".replace(",", " "),
                    )
                except Exception:
                    pass

            fig_donut = _donut_types(tour, nom)
            if fig_donut:
                st.plotly_chart(fig_donut, use_container_width=True)
                _legende_hebergements()

    if any(t > 0 for t in totaux):
        max_val = max(max(totaux) * 1.3, 10)
        g1, g2 = st.columns(2)

        with g1:
            if totaux[0] > 0:
                st.markdown("<div style='height:200px;'>", unsafe_allow_html=True)
                st.plotly_chart(
                    _gauge_hebergements(totaux[0], nom1, COULEUR_V1, int(max_val)),
                    use_container_width=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

        with g2:
            if totaux[1] > 0:
                st.markdown("<div style='height:200px;'>", unsafe_allow_html=True)
                st.plotly_chart(
                    _gauge_hebergements(totaux[1], nom2, COULEUR_V2, int(max_val)),
                    use_container_width=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("Points d'intérêt (OpenStreetMap)")
    st.caption("Source : API Overpass / OpenStreetMap — rayon 8km. Licence ODbL.")

    lat1 = ville1.get("latitude")
    lon1 = ville1.get("longitude")
    lat2 = ville2.get("latitude")
    lon2 = ville2.get("longitude")

    if not all([lat1, lon1, lat2, lon2]):
        st.warning("Coordonnées manquantes.")
        return

    with st.spinner("Chargement des points d'intérêt..."):
        poi1_counts, poi1_points = get_poi_touristiques(float(lat1), float(lon1))
        poi2_counts, poi2_points = get_poi_touristiques(float(lat2), float(lon2))

    st.subheader("Cartes touristiques interactives")
    colA, colB = st.columns(2)
    with colA:
        st.markdown(f"### {nom1}")
        deck1 = carte_poi_tourisme(poi1_points, lat1, lon1)
        if deck1:
            st.pydeck_chart(deck1, height=400)
    with colB:
        st.markdown(f"### {nom2}")
        deck2 = carte_poi_tourisme(poi2_points, lat2, lon2)
        if deck2:
            st.pydeck_chart(deck2, height=400)

    _legende_couleurs()
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"<h4 style='color:{COULEUR_V1};'>{nom1}</h4>", unsafe_allow_html=True
        )
        for k, v in poi1_counts.items():
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:4px 0;">'
                f'<span style="font-weight:500;color:#111;">{k}</span>'
                f'<span style="font-weight:600;">{v}</span></div>',
                unsafe_allow_html=True,
            )
    with col2:
        st.markdown(
            f"<h4 style='color:{COULEUR_V2};'>{nom2}</h4>", unsafe_allow_html=True
        )
        for k, v in poi2_counts.items():
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:4px 0;">'
                f'<span style="font-weight:500;color:#111;">{k}</span>'
                f'<span style="font-weight:600;">{v}</span></div>',
                unsafe_allow_html=True,
            )

    st.divider()

    tab1, tab2 = st.tabs(["Barres comparatives", "Radar touristique"])
    with tab1:
        st.plotly_chart(
            _bar_poi(poi1_counts, poi2_counts, nom1, nom2),
            use_container_width=True,
        )
    with tab2:
        st.plotly_chart(
            _radar_tourisme(poi1_counts, poi2_counts, nom1, nom2),
            use_container_width=True,
        )
