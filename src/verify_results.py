from pathlib import Path

import duckdb
import pandas as pd


RAW_FILE = Path("data/raw/vgsales.csv")
GOLD_GENRE_FILE = Path("data/processed/sales_by_genre.parquet")

for required_file in [RAW_FILE, GOLD_GENRE_FILE]:
    if not required_file.exists():
        raise FileNotFoundError(f"Fichier introuvable : {required_file}")


print("=== Vérification indépendante avec pandas ===")

raw_data = pd.read_csv(
    RAW_FILE,
    na_values=["N/A"],
)

# Normalisation identique au traitement Silver
raw_data["Name"] = raw_data["Name"].str.strip()
raw_data["Platform"] = raw_data["Platform"].str.strip().str.upper()
raw_data["Genre"] = raw_data["Genre"].str.strip()
raw_data["Publisher"] = (
    raw_data["Publisher"]
    .fillna("Unknown")
    .str.strip()
    .replace("", "Unknown")
)

# Suppression du même doublon que dans la transformation Silver
deduplicated_data = raw_data.drop_duplicates(
    subset=[
        "Name",
        "Platform",
        "Year",
        "Genre",
        "Publisher",
        "NA_Sales",
        "EU_Sales",
        "JP_Sales",
        "Other_Sales",
    ],
    keep="first",
).copy()

# Recalcul indépendant des ventes mondiales
deduplicated_data["calculated_global_sales"] = (
    deduplicated_data["NA_Sales"]
    + deduplicated_data["EU_Sales"]
    + deduplicated_data["JP_Sales"]
    + deduplicated_data["Other_Sales"]
).round(2)

# Agrégation indépendante avec pandas
pandas_genre_result = (
    deduplicated_data.groupby("Genre", as_index=False)
    .agg(
        number_of_games=("Name", "nunique"),
        global_sales=("calculated_global_sales", "sum"),
    )
    .sort_values("global_sales", ascending=False)
)

pandas_genre_result["global_sales"] = (
    pandas_genre_result["global_sales"].round(2)
)

print("\nRésultat pandas par genre :")
print(pandas_genre_result.to_string(index=False))


print("\n=== Résultat Gold produit avec DuckDB ===")

gold_genre_result = duckdb.sql(
    """
    SELECT
        genre,
        number_of_games,
        CAST(global_sales AS DOUBLE) AS global_sales
    FROM read_parquet('data/processed/sales_by_genre.parquet')
    ORDER BY global_sales DESC
    """
).fetchdf()

print(gold_genre_result.to_string(index=False))


comparison = pandas_genre_result.merge(
    gold_genre_result,
    left_on="Genre",
    right_on="genre",
    suffixes=("_pandas", "_gold"),
)

comparison["sales_difference"] = (
    comparison["global_sales_pandas"]
    - comparison["global_sales_gold"]
).abs().round(2)

comparison["games_difference"] = (
    comparison["number_of_games_pandas"]
    - comparison["number_of_games_gold"]
).abs()


print("\n=== Comparaison pandas / Gold ===")

print(
    comparison[
        [
            "Genre",
            "global_sales_pandas",
            "global_sales_gold",
            "sales_difference",
            "number_of_games_pandas",
            "number_of_games_gold",
            "games_difference",
        ]
    ].to_string(index=False)
)


maximum_sales_difference = comparison["sales_difference"].max()
maximum_games_difference = comparison["games_difference"].max()

if maximum_sales_difference > 0.01:
    raise AssertionError(
        "Échec : les ventes pandas et Gold sont différentes."
    )

if maximum_games_difference != 0:
    raise AssertionError(
        "Échec : le nombre de jeux pandas et Gold est différent."
    )


best_genre_pandas = pandas_genre_result.iloc[0]["Genre"]
best_genre_gold = gold_genre_result.iloc[0]["genre"]

if best_genre_pandas != best_genre_gold:
    raise AssertionError(
        "Échec : le genre dominant diffère entre pandas et Gold."
    )


print("\n=== Résultat de la vérification ===")
print(f"Genre dominant avec pandas : {best_genre_pandas}")
print(f"Genre dominant dans Gold   : {best_genre_gold}")
print(f"Écart maximal des ventes   : {maximum_sales_difference:.2f}")
print(f"Écart maximal du nombre de jeux : {maximum_games_difference}")
print("Vérification indépendante réussie.")