"""
app.py - Point d'entrée Streamlit
Comparateur de villes françaises (+20 000 habitants)
"""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from utils import load_villes
from components.general      import afficher_section_generale
from components.meteo         import afficher_section_meteo
from components.immobilier    import afficher_section_immobilier
from components.emploi        import afficher_section_emploi
from components.equipments    import afficher_section_equipements
from components.tourisme      import afficher_section_tourisme

st.set_page_config(
    page_title="Comparateur de Villes Françaises",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Styles généraux ──────────────────────────────────────────────────────────
st.markdown("""
<style>
.main-title    { font-size:4rem; font-weight:800; color:#1E293B; margin-bottom:0; text-align:center; }
.main-subtitle { font-size:1rem; color:#64748B; margin-top:0.2rem; margin-bottom:1.5rem; text-align:center; }
.ville-badge-1 { background:#EFF6FF; border-left:4px solid #2563EB; padding:0.5rem 1rem; border-radius:0 8px 8px 0; margin-bottom:0.5rem; }
.ville-badge-2 { background:#FEF2F2; border-left:4px solid #DC2626; padding:0.5rem 1rem; border-radius:0 8px 8px 0; margin-bottom:0.5rem; }
</style>
""", unsafe_allow_html=True)

# ─── Correctif PyDeck ─────────────────────────────────────────────────────────
st.markdown("""
<style>
.stDeckGlJsonChart { background-color: transparent !important; }
.stDeckGlJsonChart canvas { background-color: transparent !important; }
canvas { background-color: transparent !important; }
</style>
""", unsafe_allow_html=True)

# ─── Titre principal ──────────────────────────────────────────────────────────
st.markdown("<div class='main-title'>Comparateur de Villes Françaises</div>", unsafe_allow_html=True)
st.markdown("<div class='main-subtitle'>Comparez deux villes françaises sur leurs données générales, emploi, logement, météo, équipements et tourisme.</div>", unsafe_allow_html=True)

# ─── Chargement ───────────────────────────────────────────────────────────────
df_villes = load_villes()
if df_villes.empty:
    st.error("❌ Aucune donnée. Lancez : python scripts/fetch_all.py")
    st.stop()

liste_villes = sorted(df_villes["nom_standard"].dropna().unique().tolist())

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; margin-bottom:15px;">
        <img src="https://upload.wikimedia.org/wikipedia/fr/e/e7/Logo_Universit%C3%A9_de_Paris.svg"
        style="width:120px;">
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("## Sélection des villes")
    st.caption("Communes de plus de 20 000 habitants (source : INSEE)")

    default1 = "Lyon"     if "Lyon"     in liste_villes else liste_villes[0]
    default2 = "Bordeaux" if "Bordeaux" in liste_villes else liste_villes[1]

    ville1_nom = st.selectbox("🔵 Ville 1", liste_villes, index=liste_villes.index(default1))
    ville2_nom = st.selectbox("🔴 Ville 2", liste_villes, index=liste_villes.index(default2))

    if ville1_nom == ville2_nom:
        st.warning("⚠️ Sélectionnez deux villes différentes.")

    st.divider()
    st.markdown("## Sections")
    show_general     = st.checkbox("Données générales",      value=True)
    show_emploi      = st.checkbox("Emploi & Chômage",       value=True)
    show_immobilier  = st.checkbox("Logement & Immobilier",  value=True)
    show_meteo       = st.checkbox("Météo & Climat",         value=True)
    show_equipements = st.checkbox("Équipements & Services", value=True)
    show_tourisme    = st.checkbox("Tourisme & Attractivité",value=True)

    st.divider()
    st.caption(
        "**Sources**\n\n"
        "- INSEE / data.gouv.fr\n"
        "- DVF (DGFiP)\n"
        "- Open-Meteo\n"
        "- OpenStreetMap / Overpass\n"
        "- Wikipedia"
    )

# ─── Données des villes ───────────────────────────────────────────────────────
def get_ville(nom):
    row = df_villes[df_villes["nom_standard"] == nom]
    return row.iloc[0].to_dict() if not row.empty else {}

ville1 = get_ville(ville1_nom)
ville2 = get_ville(ville2_nom)

# ─── En-tête des villes ───────────────────────────────────────────────────────
col_h1, col_h2 = st.columns(2)
with col_h1:
    st.markdown(f'<div class="ville-badge-1">🔵 <strong>{ville1_nom}</strong> — {ville1.get("dep_nom","")} ({ville1.get("reg_nom","")})</div>', unsafe_allow_html=True)
with col_h2:
    st.markdown(f'<div class="ville-badge-2">🔴 <strong>{ville2_nom}</strong> — {ville2.get("dep_nom","")} ({ville2.get("reg_nom","")})</div>', unsafe_allow_html=True)

st.divider()

# ─── Sections ─────────────────────────────────────────────────────────────────
if ville1_nom == ville2_nom:
    st.warning("⚠️ Sélectionnez deux villes différentes dans la barre latérale.")
    st.stop()

if show_general:
    afficher_section_generale(ville1, ville2)
    st.divider()

if show_emploi:
    afficher_section_emploi(ville1, ville2)
    st.divider()

if show_immobilier:
    afficher_section_immobilier(ville1, ville2)
    st.divider()

if show_meteo:
    afficher_section_meteo(ville1, ville2)
    st.divider()

if show_equipements:
    afficher_section_equipements(ville1, ville2)
    st.divider()

if show_tourisme:
    afficher_section_tourisme(ville1, ville2)

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("SAE Outils Décisionnels — données issues de sources publiques ouvertes (INSEE, data.gouv.fr, Open-Meteo, OpenStreetMap, Wikipedia).")
st.markdown("""
<style>
.footer { width:100%; text-align:center; padding:15px 0; margin-top:40px; color:#64748B; font-size:0.9rem; }
</style>
<div class="footer">© 2026 Assia BOUDJRAF — Tous droits réservés</div>
""", unsafe_allow_html=True)

