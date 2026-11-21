# Projet Big Data - Analyse des ventes de jeux vidéo

## Auteur

BELCHGUER Ayyub

## Prérequis

- Compte Onyxia avec accès au stockage S3
- Python 3
- Git
- Bibliothèques Python : DuckDB et pandas

Installation :

```bash
python -m pip install duckdb pandas pyarrow
```

## Jeu de données

- **Nom :** Video Games Sales
- **Auteur :** Gregory Smith
- **Source :** Zenodo
- **URL :** https://zenodo.org/records/5898311
- **DOI :** https://doi.org/10.5281/zenodo.5898311
- **Licence :** Creative Commons Attribution 4.0 International
- **Date de téléchargement :** 21 novembre 2026
- **Fichier brut :** `vgsales.csv`
- **Taille brute :** 1 355 781 octets, soit environ 1,3 Mo
- **Nombre d'observations :** 16 598
- **Format :** CSV
- **MD5 :** `67fa6f5efdc100db4586aa80556e8620`

Le dataset contient les ventes régionales et mondiales de jeux vidéo ayant dépassé 100 000 exemplaires vendus. Les données proviennent de VGChartz et sont publiées sur Zenodo.

## Problématique

Quels genres de jeux vidéo réalisent les meilleures ventes selon les régions, notamment en Amérique du Nord, en Europe et au Japon ? Le projet étudie également l'évolution des ventes mondiales au fil du temps. Le résultat principal est vérifié indépendamment avec pandas.

## Chemins S3

- **Données brutes :** `s3://user-a-belchguer-ece/bigdata_project2/raw/vgsales.csv`
- **Données traitées :** `s3://user-a-belchguer-ece/bigdata_project2/processed/`

## Procédure de reproduction

### 1. Récupérer le projet et les données

```bash
git clone https://github.com/Ayyub92i/bigdata_project2.git
cd bigdata_project2
mkdir -p data/raw
wget -O data/raw/vgsales.csv \
"https://zenodo.org/records/5898311/files/vgsales.csv"
md5sum data/raw/vgsales.csv
```

### 2. Installer les dépendances

```bash
python -m pip install duckdb pandas pyarrow
```

### 3. Exécuter le contrôle qualité

```bash
python src/check_data.py
```

### 4. Exécuter le pipeline Bronze, Silver et Gold

```bash
python src/transform_data.py
```

Le pipeline supprime un doublon exact, remplace les éditeurs absents par `Unknown`, recalcule les ventes mondiales et produit :

```text
data/processed/silver_games.parquet
data/processed/sales_by_genre.parquet
data/processed/sales_by_region.parquet
data/processed/sales_by_year.parquet
```

### 5. Vérifier indépendamment les résultats

```bash
python src/verify_results.py
```

Cette commande recalcule les ventes par genre avec pandas et les compare au résultat Gold produit avec DuckDB. Le résultat attendu est `Action`, avec un écart maximal de `0,00`.

### 6. Reprendre après un arrêt

```bash
cd /home/onyxia/work/bigdata_project2
git pull
python src/transform_data.py
python src/verify_results.py
```

Les scripts recréent les fichiers Parquet et peuvent être relancés sans modifier le CSV brut. Les données brutes et traitées sont également conservées dans le bucket S3.