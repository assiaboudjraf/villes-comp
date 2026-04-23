"""
utils.py - Fonctions utilitaires partagées
"""

import os
import requests
import pandas as pd
import streamlit as st
from datetime import date, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


# ─── Chargement données statiques ────────────────────────────────────────────

@st.cache_data
def load_villes() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "villes_20000.csv")
    if not os.path.exists(path):
        st.error("❌ Fichier data/villes_20000.csv introuvable. Lancez : python scripts/fetch_all.py")
        return pd.DataFrame()

    df = pd.read_csv(path, dtype={"code_insee": str})

    # 🔧 Correction : forcer les colonnes latitude / longitude en float
    if "latitude" in df.columns:
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    if "longitude" in df.columns:
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    # 🔧 Supprimer les lignes invalides
    df = df.dropna(subset=["latitude", "longitude"])

    return df


@st.cache_data
def load_immobilier() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "immobilier.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, dtype={"code_insee": str})

@st.cache_data
def load_chomage() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "chomage.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, dtype={"code_insee": str})


# ─── API Météo Open-Meteo ─────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_meteo_previsions(lat: float, lon: float) -> dict:
    """
    Prévisions 7 jours — Open-Meteo Forecast API
    https://api.open-meteo.com/v1/forecast
    Gratuit, sans clé API. Licence CC BY 4.0
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode,windspeed_10m_max",
        "timezone": "Europe/Paris",
        "forecast_days": 7,
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=86400)
def get_meteo_historique(lat: float, lon: float) -> dict:
    """
    Normales climatiques mensuelles sur 5 ans (données horaires agrégées)
    Open-Meteo Historical Weather API — /v1/archive
    Paramètres hourly (pas monthly qui n'existe pas)
    """
    # Dernières 5 années complètes
    end   = date(date.today().year - 1, 12, 31)
    start = date(end.year - 4, 1, 1)

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "start_date": start.isoformat(),
        "end_date":   end.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum",
        "timezone": "Europe/Paris",
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        # Vérifier qu'on a bien des données
        if "daily" not in data or not data["daily"].get("time"):
            return {"error": "Pas de données daily dans la réponse"}
        return data
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=86400)
def get_wikipedia_resume(ville_nom: str) -> str:
    """Wikipedia REST API — résumé de la ville"""
    url = f"https://fr.wikipedia.org/api/rest_v1/page/summary/{ville_nom}"
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "ComparateurVilles/1.0"})
        r.raise_for_status()
        return r.json().get("extract", "Aucune description disponible.")
    except Exception:
        return "Aucune description disponible."


# ─── Codes météo WMO ──────────────────────────────────────────────────────────

WMO_CODES = {
    0: ("Ciel dégagé", "☀️"), 1: ("Principalement dégagé", "🌤️"),
    2: ("Partiellement nuageux", "⛅"), 3: ("Couvert", "☁️"),
    45: ("Brouillard", "🌫️"), 48: ("Brouillard givrant", "🌫️"),
    51: ("Bruine légère", "🌦️"), 53: ("Bruine modérée", "🌦️"), 55: ("Bruine dense", "🌧️"),
    61: ("Pluie légère", "🌧️"), 63: ("Pluie modérée", "🌧️"), 65: ("Pluie forte", "🌧️"),
    71: ("Neige légère", "🌨️"), 73: ("Neige modérée", "❄️"), 75: ("Neige forte", "❄️"),
    80: ("Averses légères", "🌦️"), 81: ("Averses modérées", "🌧️"), 82: ("Averses violentes", "⛈️"),
    95: ("Orage", "⛈️"), 99: ("Orage avec grêle", "⛈️"),
}

def decode_wmo(code: int) -> tuple:
    return WMO_CODES.get(int(code), ("Inconnu", "❓"))


COULEUR_V1 = "#2563EB"
COULEUR_V2 = "#DC2626"


