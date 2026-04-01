import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.ingest_escom_receipt import add_token

if __name__ == "__main__":
    result = add_token(
        "592152026031381201737",
        "37154345799",
        59.9,
        20000,
        "14/03/2026 15:00:00",
    )
    print(result)
