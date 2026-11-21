# Projet Big Data - Analyse des ventes de jeux vidéo

## Auteur

- BELCHGUER Ayyub

## Prérequis

Pour reproduire ce projet, il faut disposer des éléments suivants :

- un compte Onyxia ;
- un accès au stockage S3 d'Onyxia ;
- Python 3 ;
- DuckDB ;
- dbt-duckdb ;
- Git.

Installation des dépendances :

```bash
pip install duckdb pandas pyarrow dbt-duckdb boto3
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
- **Empreinte MD5 :** `67fa6f5efdc100db4586aa80556e8620`

Le fichier contient les ventes régionales et mondiales de jeux vidéo ayant dépassé 100 000 exemplaires vendus. Les données proviennent de VGChartz et ont été publiées sur Zenodo.

## Problématique

Quels genres de jeux vidéo réalisent les meilleures ventes selon les régions, notamment en Amérique du Nord, en Europe et au Japon ? Le projet étudie également l'évolution des ventes mondiales au fil du temps. Les résultats sont produits à l'aide d'un pipeline reproductible exécuté sur Onyxia.

## Chemins S3

- **Données brutes :** `s3://user-a-belchguer-ece/bigdata_project2/raw/vgsales.csv`
- **Données traitées :** `s3://user-a-belchguer-ece/bigdata_project2/processed/`

## Procédure de reproduction

### 1. Cloner le dépôt

```bash
git clone https://github.com/Ayyub92i/bigdata_project2.git
cd bigdata_project2
```

### 2. Installer les dépendances

```bash
pip install duckdb pandas pyarrow dbt-duckdb boto3
```

### 3. Télécharger les données brutes

```bash
mkdir -p data/raw
wget -O data/raw/vgsales.csv \
"https://zenodo.org/records/5898311/files/vgsales.csv"
```

Vérifier le fichier téléchargé :

```bash
wc -l data/raw/vgsales.csv
stat -c "%s octets" data/raw/vgsales.csv
md5sum data/raw/vgsales.csv
```

### 4. Déposer les données brutes dans S3

Configurer les variables d'environnement S3 fournies par Onyxia, puis exécuter :

```bash
python src/upload_to_s3.py
```

Les identifiants S3 et les clés d'accès ne doivent jamais être ajoutés au dépôt Git.

### 5. Vérifier la qualité des données

```bash
python src/check_data.py
```

### 6. Exécuter les transformations

```bash
cd src/dbt_project
dbt run
dbt test
```

### 7. Produire et vérifier les résultats

```bash
cd ../..
python src/export_results.py
python src/verify_results.py
```

Les résultats finaux sont exportés au format Parquet dans le préfixe S3 `processed`.

### 8. Reprendre après un arrêt

Après le redémarrage du service Onyxia :

```bash
cd /home/onyxia/work/bigdata_project2
git pull
```

Il faut ensuite vérifier les variables S3 et relancer uniquement l'étape qui a échoué. Les transformations sont reproductibles et ne modifient jamais le fichier brut.