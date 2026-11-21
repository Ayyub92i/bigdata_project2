from pathlib import Path

import duckdb


# Chemin du fichier CSV depuis la racine du projet
CSV_PATH = Path("data/raw/vgsales.csv")

# Vérification de l'existence du fichier
if not CSV_PATH.exists():
    raise FileNotFoundError(
        f"Fichier introuvable : {CSV_PATH}\n"
        "Téléchargez vgsales.csv dans data/raw/ avant de lancer le script."
    )

# Conversion en chemin absolu compatible avec une requête SQL DuckDB
csv_path_sql = str(CSV_PATH.resolve()).replace("'", "''")

# Connexion DuckDB en mémoire
connection = duckdb.connect()

try:
    # Lecture du CSV et création d'une vue temporaire
    connection.execute(
        f"""
        CREATE OR REPLACE VIEW raw_games AS
        SELECT *
        FROM read_csv_auto(
            '{csv_path_sql}',
            header = true,
            nullstr = 'N/A'
        )
        """
    )

    # Affichage du schéma détecté par DuckDB
    schema = connection.execute(
        """
        DESCRIBE raw_games
        """
    ).fetchdf()

    print("\n=== Schéma détecté par DuckDB ===")
    print(schema.to_string(index=False))

    # Résumé général de la qualité des données
    summary = connection.execute(
        """
        SELECT
            COUNT(*) AS total_rows,

            COUNT(*) - COUNT(Year) AS missing_year,
            COUNT(*) - COUNT(Genre) AS missing_genre,
            COUNT(*) - COUNT(Publisher) AS missing_publisher,

            COUNT(DISTINCT Name) AS distinct_games,
            COUNT(DISTINCT Platform) AS distinct_platforms,
            COUNT(DISTINCT Genre) AS distinct_genres,
            COUNT(DISTINCT Publisher) AS distinct_publishers,

            SUM(
                CASE
                    WHEN NA_Sales < 0
                      OR EU_Sales < 0
                      OR JP_Sales < 0
                      OR Other_Sales < 0
                      OR Global_Sales < 0
                    THEN 1
                    ELSE 0
                END
            ) AS rows_with_negative_sales,

            SUM(
                CASE
                    WHEN ABS(
                        Global_Sales
                        - (
                            NA_Sales
                            + EU_Sales
                            + JP_Sales
                            + Other_Sales
                        )
                    ) > 0.02
                    THEN 1
                    ELSE 0
                END
            ) AS inconsistent_global_sales

        FROM raw_games
        """
    ).fetchdf()

    print("\n=== Résumé de la qualité des données ===")
    print(summary.to_string(index=False))

    # Vérification des années
    years = connection.execute(
        """
        SELECT
            MIN(Year) AS minimum_year,
            MAX(Year) AS maximum_year,

            SUM(
                CASE
                    WHEN Year IS NOT NULL
                     AND (Year < 1980 OR Year > 2020)
                    THEN 1
                    ELSE 0
                END
            ) AS implausible_years

        FROM raw_games
        """
    ).fetchdf()

    print("\n=== Vérification des années ===")
    print(years.to_string(index=False))

    # Recherche des doublons exacts
    duplicates = connection.execute(
        """
        SELECT
            COUNT(*) AS duplicate_groups,
            COALESCE(SUM(duplicate_count - 1), 0) AS duplicate_rows
        FROM (
            SELECT
                Name,
                Platform,
                Year,
                Genre,
                Publisher,
                NA_Sales,
                EU_Sales,
                JP_Sales,
                Other_Sales,
                Global_Sales,
                COUNT(*) AS duplicate_count
            FROM raw_games
            GROUP BY
                Name,
                Platform,
                Year,
                Genre,
                Publisher,
                NA_Sales,
                EU_Sales,
                JP_Sales,
                Other_Sales,
                Global_Sales
            HAVING COUNT(*) > 1
        ) AS duplicate_data
        """
    ).fetchdf()

    print("\n=== Vérification des doublons exacts ===")
    print(duplicates.to_string(index=False))

    # Exemples de lignes contenant des valeurs manquantes
    missing_examples = connection.execute(
        """
        SELECT
            Rank,
            Name,
            Platform,
            Year,
            Genre,
            Publisher
        FROM raw_games
        WHERE Year IS NULL
           OR Genre IS NULL
           OR Publisher IS NULL
        ORDER BY Rank
        LIMIT 10
        """
    ).fetchdf()

    print("\n=== Exemples de valeurs manquantes ===")

    if missing_examples.empty:
        print("Aucune valeur manquante détectée dans Year, Genre ou Publisher.")
    else:
        print(missing_examples.to_string(index=False))

    # Exemples d'incohérences entre les ventes régionales et mondiales
    inconsistent_examples = connection.execute(
        """
        SELECT
            Rank,
            Name,
            Platform,
            NA_Sales,
            EU_Sales,
            JP_Sales,
            Other_Sales,
            Global_Sales,

            ROUND(
                NA_Sales
                + EU_Sales
                + JP_Sales
                + Other_Sales,
                2
            ) AS calculated_global_sales,

            ROUND(
                Global_Sales
                - (
                    NA_Sales
                    + EU_Sales
                    + JP_Sales
                    + Other_Sales
                ),
                2
            ) AS difference

        FROM raw_games

        WHERE ABS(
            Global_Sales
            - (
                NA_Sales
                + EU_Sales
                + JP_Sales
                + Other_Sales
            )
        ) > 0.02

        ORDER BY ABS(
            Global_Sales
            - (
                NA_Sales
                + EU_Sales
                + JP_Sales
                + Other_Sales
            )
        ) DESC

        LIMIT 10
        """
    ).fetchdf()

    print("\n=== Exemples d'incohérences des ventes mondiales ===")

    if inconsistent_examples.empty:
        print("Aucune incohérence supérieure à 0,02 million détectée.")
    else:
        print(inconsistent_examples.to_string(index=False))

    # Répartition des lignes par genre
    genre_distribution = connection.execute(
        """
        SELECT
            Genre,
            COUNT(*) AS number_of_games,
            ROUND(SUM(Global_Sales), 2) AS total_global_sales
        FROM raw_games
        WHERE Genre IS NOT NULL
        GROUP BY Genre
        ORDER BY total_global_sales DESC
        """
    ).fetchdf()

    print("\n=== Répartition et ventes par genre ===")
    print(genre_distribution.to_string(index=False))

    print("\nContrôle qualité terminé avec succès.")

finally:
    connection.close()