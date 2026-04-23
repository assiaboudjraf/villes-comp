"""
components/general.py
----------------------
Affiche les données générales d'une ville : population, superficie, densité,
description Wikipedia, localisation.
"""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import get_wikipedia_resume, COULEUR_V1, COULEUR_V2


def afficher_section_generale(ville1: dict, ville2: dict):
    """
    Affiche en deux colonnes les données générales des deux villes sélectionnées.
    
    Paramètres
    ----------
    ville1, ville2 : dict
        Ligne du DataFrame villes_20000.csv convertie en dict.
    """
    st.header("Données générales")

    col1, col2 = st.columns(2)

    for col, ville, couleur in [(col1, ville1, COULEUR_V1), (col2, ville2, COULEUR_V2)]:
        with col:
            nom = ville.get("nom_standard", "—")
            dep = ville.get("dep_nom", "—")
            reg = ville.get("reg_nom", "—")
            pop = ville.get("population", None)
            superficie = ville.get("superficie", None)
            densite = ville.get("densite", None)

            st.markdown(
                f"<h3 style='color:{couleur};'>{nom}</h3>",
                unsafe_allow_html=True
            )

            # Métriques clés
            m1, m2, m3 = st.columns(3)
            m1.metric("Population", f"{int(pop):,}".replace(",", " ") if pop else "—")
            m2.metric("Superficie", f"{superficie:.1f} km²" if superficie else "—")
            m3.metric("Densité", f"{densite:.0f} hab/km²" if densite else "—")

            # Localisation
            st.markdown(f"📍 **{dep}** — {reg}")
            st.markdown(f"🏷️ Code INSEE : `{ville.get('code_insee', '—')}`")
            st.markdown(f"📬 Code postal : `{ville.get('code_postal', '—')}`")

            # Description Wikipedia
            with st.expander("Description (Wikipedia)"):
                resume = get_wikipedia_resume(nom)
                st.write(resume)

    # Tableau comparatif
    st.subheader("Comparaison rapide")
    data_compare = {
        "Indicateur": ["Population", "Superficie (km²)", "Densité (hab/km²)", "Département", "Région"],
        ville1.get("nom_standard", "Ville 1"): [
            f"{int(ville1.get('population', 0)):,}".replace(",", " "),
            f"{ville1.get('superficie', '—')}",
            f"{ville1.get('densite', '—'):.0f}" if ville1.get('densite') else "—",
            ville1.get("dep_nom", "—"),
            ville1.get("reg_nom", "—"),
        ],
        ville2.get("nom_standard", "Ville 2"): [
            f"{int(ville2.get('population', 0)):,}".replace(",", " "),
            f"{ville2.get('superficie', '—')}",
            f"{ville2.get('densite', '—'):.0f}" if ville2.get('densite') else "—",
            ville2.get("dep_nom", "—"),
            ville2.get("reg_nom", "—"),
        ],
    }
    import pandas as pd
    st.dataframe(pd.DataFrame(data_compare), hide_index=True, use_container_width=True)
