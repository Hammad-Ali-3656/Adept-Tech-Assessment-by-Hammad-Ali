"""Train the churn model and save artifacts.

Usage:  python -m scripts.train
"""
import json

from src.data_prep import load_clean, save_clean
from src.model import train_and_save


def main():
    df = load_clean()
    save_clean(df)
    print(f"Cleaned dataset: {df.shape[0]} rows, churn rate "
          f"{(df['Churn'] == 'Yes').mean():.1%}")
    model = train_and_save(verbose=True)
    print("\nSelected:", model.metrics["selected_model"])
    print(json.dumps(model.metrics["validation"], indent=2))


if __name__ == "__main__":
    main()
