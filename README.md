# 🏙️ Comparateur de Villes Françaises

Application web permettant de comparer **deux villes françaises de plus de 20 000 habitants** sur plusieurs dimensions :

- Données générales  
- Emploi et chômage  
- Logement et immobilier  
- Météo (prévisions + climatologie)  
- Équipements culturels et sportifs  

L’objectif est de fournir une visualisation claire et interactive pour analyser rapidement les différences entre deux territoires.

---

## 📁 Structure du projet

projet_villes/
│
├── README.md                    Documentation du projet
├── requirements.txt             Dépendances Python
│
├── .streamlit/
│   └── config.toml              Thème Streamlit
│
├── data/                        Données statiques générées par les scripts
│   ├── villes_20000.csv         Villes françaises >20 000 hab (INSEE)
│   ├── immobilier.csv           Prix immobilier (DVF agrégé)
│   ├── immobilier_raw.csv       Données DVF brutes (avant agrégation)
│   ├── chomage.csv              Taux de chômage par zone d'emploi (INSEE)
│   ├── chomage_raw.csv          Données chômage brutes (avant traitement)
│   ├── communes_france_raw.csv  Communes françaises (données brutes)
│   └── appartenance_communes.csv  Appartenance commune → zone d'emploi
│
├── scripts/                     Scripts de collecte et préparation
│   ├── fetch_villes.py          Récupération des villes françaises
│   ├── fetch_immobilier.py      Récupération des prix immobiliers (DVF)
│   ├── fetch_chomage.py         Récupération des taux de chômage (INSEE)
│   └── fetch_all.py             Exécute tous les scripts
│
└── app/
├── app.py                   Application Streamlit principale
├── components/
│   ├── general.py           Données générales
│   ├── emploi.py            Emploi et chômage
│   ├── immobilier.py        Logement et immobilier
│   ├── meteo.py             Météo et climat
│   └── equipements.py       Équipements culturels et sportifs
└── utils.py                 Fonctions utilitaires


---

## 🚀 Installation et lancement

```bash
# 1. Cloner ou dézipper le projet
cd projet_villes

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Télécharger les données (à faire une seule fois)
python scripts/fetch_all.py

# 4. Lancer l'application
streamlit run app/app.py


## Sources de données

-  Villes +20k habitants : data.gouv.fr - Licence Ouverte v2.0

- Prix immobilier (DVF agrégé) : Boris Méricskay - Licence Ouverte v2.0

- Taux de chômage (zones d'emploi) : INSEE -  Licence Ouverte v2.0

- Météo prévisions : Open-Meteo API - CC BY 4.0

- Météo historique : Open-Meteo ERA5 - CC BY 4.0

- Descriptions des villes : Wikipedia REST API - CC BY-SA 3.0


Déploiement sur Streamlit Cloud
Envoyer le projet sur GitHub

Aller sur : https://streamlit.io/cloud

Connecter le dépôt GitHub

Indiquer app/app.py comme fichier principal

Déployer

⚠️ Le dossier data/ doit être présent dans le dépôt pour que l’application fonctionne en ligne.