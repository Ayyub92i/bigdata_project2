# Projet Big Data - Analyse des ventes de jeux vidéo

## Auteur

- BELCHGUER Ayyub

## Prérequis

Pour reproduire ce projet, il faut disposer des éléments suivants :

- Un compte Onyxia
- Un accès au stockage S3 d'Onyxia
- Python 3
- DuckDB
- dbt-duckdb
- Git

## Jeu de données

- **Nom :** Video Game Sales
- **Source :** À compléter
- **URL :** À compléter
- **Licence :** À vérifier
- **Date de téléchargement :** À compléter
- **Taille des données brutes :** À vérifier, entre 1 Mo et 5 Mo
- **Format :** CSV

L'URL, la licence et la taille exacte seront ajoutées après la sélection et la vérification du jeu de données.

## Problématique

L'objectif de ce projet est d'identifier les genres de jeux vidéo ayant réalisé les meilleures ventes en Amérique du Nord, en Europe et au Japon. Le projet permettra également d'étudier l'évolution des ventes mondiales au fil du temps. Les résultats seront produits à l'aide d'un pipeline de données reproductible exécuté sur Onyxia.

## Chemins S3

- **Données brutes :** `s3://NOM_DU_BUCKET/bigdata_project2/raw/`
- **Données traitées :** `s3://NOM_DU_BUCKET/bigdata_project2/processed/`

Le nom exact du bucket sera ajouté après le dépôt des données sur le stockage S3 d'Onyxia.

## Procédure de reproduction

### 1. Cloner le dépôt Git

```bash
git clone https://github.com/Ayyub92i/bigdata_project2.git
cd bigdata_project2