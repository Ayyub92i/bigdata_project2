from pathlib import Path

import duckdb


# ============================================================
# Configuration des chemins
# ============================================================

RAW_FILE = Path("data/raw/vgsales.csv")
PROCESSED_DIRECTORY = Path("data/processed")

SILVER_FILE = PROCESSED_DIRECTORY / "silver_games.parquet"
GOLD_GENRE_FILE = PROCESSED_DIRECTORY / "sales_by_genre.parquet"
GOLD_REGION_FILE = PROCESSED_DIRECTORY / "sales_by_region.parquet"
GOLD_YEAR_FILE = PROCESSED_DIRECTORY / "sales_by_year.parquet"


# ============================================================
# Vérification des fichiers et création des dossiers
# ============================================================

if not RAW_FILE.exists():
    raise FileNotFoundError(
        f"Fichier brut introuvable : {RAW_FILE}\n"
        "Le fichier vgsales.csv doit être placé dans data/raw/."
    )

PROCESSED_DIRECTORY.mkdir(parents=True, exist_ok=True)

raw_file_sql = str(RAW_FILE.resolve()).replace("'", "''")
silver_file_sql = str(SILVER_FILE.resolve()).replace("'", "''")
gold_genre_file_sql = str(GOLD_GENRE_FILE.resolve()).replace("'", "''")
gold_region_file_sql = str(GOLD_REGION_FILE.resolve()).replace("'", "''")
gold_year_file_sql = str(GOLD_YEAR_FILE.resolve()).replace("'", "''")


# ============================================================
# Connexion à DuckDB
# ============================================================

connection = duckdb.connect()

try:
    print("\n=== 1. Lecture des données brutes ===")

    connection.execute(
        f"""
        CREATE OR REPLACE TABLE bronze_games AS
        SELECT *
        FROM read_csv_auto(
            '{raw_file_sql}',
            header = true,
            nullstr = 'N/A'
        )
        """
    )

    raw_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM bronze_games
        """
    ).fetchone()[0]

    print(f"Nombre de lignes Bronze : {raw_count}")


    # ========================================================
    # Transformation Silver
    # ========================================================

    print("\n=== 2. Création de la table Silver ===")

    connection.execute(
        """
        CREATE OR REPLACE TABLE silver_games AS

        WITH typed_data AS (
            SELECT
                CAST(Rank AS INTEGER) AS rank,
                TRIM(Name) AS name,
                UPPER(TRIM(Platform)) AS platform,
                CAST(Year AS INTEGER) AS release_year,
                TRIM(Genre) AS genre,
                COALESCE(NULLIF(TRIM(Publisher), ''), 'Unknown') AS publisher,

                CAST(NA_Sales AS DECIMAL(12, 2)) AS na_sales,
                CAST(EU_Sales AS DECIMAL(12, 2)) AS eu_sales,
                CAST(JP_Sales AS DECIMAL(12, 2)) AS jp_sales,
                CAST(Other_Sales AS DECIMAL(12, 2)) AS other_sales,

                CAST(
                    NA_Sales
                    + EU_Sales
                    + JP_Sales
                    + Other_Sales
                    AS DECIMAL(12, 2)
                ) AS global_sales,

                CAST(Global_Sales AS DECIMAL(12, 2))
                    AS original_global_sales

            FROM bronze_games
        ),

        deduplicated_data AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        name,
                        platform,
                        release_year,
                        genre,
                        publisher,
                        na_sales,
                        eu_sales,
                        jp_sales,
                        other_sales
                    ORDER BY rank
                ) AS duplicate_number

            FROM typed_data
        )

        SELECT
            rank,
            name,
            platform,
            release_year,
            genre,
            publisher,
            na_sales,
            eu_sales,
            jp_sales,
            other_sales,
            global_sales,
            original_global_sales

        FROM deduplicated_data

        WHERE duplicate_number = 1
          AND name IS NOT NULL
          AND platform IS NOT NULL
          AND genre IS NOT NULL
          AND na_sales >= 0
          AND eu_sales >= 0
          AND jp_sales >= 0
          AND other_sales >= 0
        """
    )

    silver_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM silver_games
        """
    ).fetchone()[0]

    print(f"Nombre de lignes Silver : {silver_count}")
    print(f"Nombre de doublons supprimés : {raw_count - silver_count}")


    # ========================================================
    # Contrôle de la transformation Silver
    # ========================================================

    quality_after_cleaning = connection.execute(
        """
        SELECT
            COUNT(*) AS total_rows,
            SUM(CASE WHEN publisher = 'Unknown' THEN 1 ELSE 0 END)
                AS unknown_publishers,
            SUM(CASE WHEN release_year IS NULL THEN 1 ELSE 0 END)
                AS missing_years,
            SUM(
                CASE
                    WHEN global_sales < 0
                    THEN 1
                    ELSE 0
                END
            ) AS negative_global_sales
        FROM silver_games
        """
    ).fetchdf()

    print("\n=== 3. Contrôle de la table Silver ===")
    print(quality_after_cleaning.to_string(index=False))


    # ========================================================
    # Export de la table Silver au format Parquet
    # ========================================================

    connection.execute(
        f"""
        COPY silver_games
        TO '{silver_file_sql}'
        (
            FORMAT PARQUET,
            COMPRESSION ZSTD
        )
        """
    )

    print(f"\nFichier Silver créé : {SILVER_FILE}")


    # ========================================================
    # Gold 1 : ventes mondiales par genre
    # ========================================================

    print("\n=== 4. Création de Gold : ventes par genre ===")

    connection.execute(
        """
        CREATE OR REPLACE TABLE gold_sales_by_genre AS
        SELECT
            genre,
            COUNT(*) AS number_of_rows,
            COUNT(DISTINCT name) AS number_of_games,
            ROUND(SUM(na_sales), 2) AS na_sales,
            ROUND(SUM(eu_sales), 2) AS eu_sales,
            ROUND(SUM(jp_sales), 2) AS jp_sales,
            ROUND(SUM(other_sales), 2) AS other_sales,
            ROUND(SUM(global_sales), 2) AS global_sales
        FROM silver_games
        GROUP BY genre
        ORDER BY global_sales DESC
        """
    )

    connection.execute(
        f"""
        COPY gold_sales_by_genre
        TO '{gold_genre_file_sql}'
        (
            FORMAT PARQUET,
            COMPRESSION ZSTD
        )
        """
    )


    # ========================================================
    # Gold 2 : genre dominant par région
    # ========================================================

    print("=== 5. Création de Gold : ventes par région ===")

    connection.execute(
        """
        CREATE OR REPLACE TABLE gold_sales_by_region AS

        WITH regional_sales AS (
            SELECT genre, 'Amérique du Nord' AS region, SUM(na_sales) AS sales
            FROM silver_games
            GROUP BY genre

            UNION ALL

            SELECT genre, 'Europe' AS region, SUM(eu_sales) AS sales
            FROM silver_games
            GROUP BY genre

            UNION ALL

            SELECT genre, 'Japon' AS region, SUM(jp_sales) AS sales
            FROM silver_games
            GROUP BY genre

            UNION ALL

            SELECT genre, 'Autres régions' AS region, SUM(other_sales) AS sales
            FROM silver_games
            GROUP BY genre
        )

        SELECT
            region,
            genre,
            ROUND(sales, 2) AS sales,
            DENSE_RANK() OVER (
                PARTITION BY region
                ORDER BY sales DESC
            ) AS regional_rank

        FROM regional_sales

        ORDER BY region, regional_rank, genre
        """
    )

    connection.execute(
        f"""
        COPY gold_sales_by_region
        TO '{gold_region_file_sql}'
        (
            FORMAT PARQUET,
            COMPRESSION ZSTD
        )
        """
    )


    # ========================================================
    # Gold 3 : évolution annuelle
    # ========================================================

    print("=== 6. Création de Gold : évolution annuelle ===")

    connection.execute(
        """
        CREATE OR REPLACE TABLE gold_sales_by_year AS
        SELECT
            release_year,
            COUNT(*) AS number_of_rows,
            COUNT(DISTINCT name) AS number_of_games,
            ROUND(SUM(global_sales), 2) AS global_sales
        FROM silver_games
        WHERE release_year IS NOT NULL
        GROUP BY release_year
        ORDER BY release_year
        """
    )

    connection.execute(
        f"""
        COPY gold_sales_by_year
        TO '{gold_year_file_sql}'
        (
            FORMAT PARQUET,
            COMPRESSION ZSTD
        )
        """
    )


    # ========================================================
    # Affichage des résultats principaux
    # ========================================================

    print("\n=== Résultat Gold : ventes mondiales par genre ===")

    genre_results = connection.execute(
        """
        SELECT
            genre,
            number_of_games,
            global_sales
        FROM gold_sales_by_genre
        ORDER BY global_sales DESC
        """
    ).fetchdf()

    print(genre_results.to_string(index=False))


    print("\n=== Résultat Gold : meilleur genre par région ===")

    region_results = connection.execute(
        """
        SELECT
            region,
            genre,
            sales
        FROM gold_sales_by_region
        WHERE regional_rank = 1
        ORDER BY region
        """
    ).fetchdf()

    print(region_results.to_string(index=False))


    print("\n=== Fichiers produits ===")

    for output_file in [
        SILVER_FILE,
        GOLD_GENRE_FILE,
        GOLD_REGION_FILE,
        GOLD_YEAR_FILE,
    ]:
        size_bytes = output_file.stat().st_size
        print(f"{output_file} : {size_bytes} octets")

    print("\nTransformation Bronze -> Silver -> Gold terminée avec succès.")

finally:
    connection.close()