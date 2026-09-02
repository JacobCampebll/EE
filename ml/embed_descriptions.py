r"""
One-off: embed every distinct (bid_code, description) pair with MiniLM.

    py embed_descriptions.py

Writes desc_emb.npy (float32, N x 384) and desc_keys.tsv alongside the training
data. ~1,384 pairs, about 30 seconds on CPU. Re-run only if bid_items gains new
codes or descriptions; train_embed.py reads the cache and never re-embeds.

Model: sentence-transformers/all-MiniLM-L6-v2, local and free. First run
downloads ~90 MB from the HF hub; after that it is cached under
%USERPROFILE%\.cache\huggingface.

The embedded text is "<bid_code> <description>" rather than the description
alone: the code carries real structure (the ES/EC/ND/NS suffixes group special
provisions) and the tokenizer handles it fine.
"""
import os
import numpy as np
import pandas as pd

DATA_DIR = os.environ.get("EE_ML_DIR", r"C:\EE\ml\data")
MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def main():
    ln = pd.read_csv(os.path.join(DATA_DIR, "lines.tsv"), sep="\t", header=None,
                     names=["ci", "bid_code", "quantity", "unit", "section",
                            "binder_grade", "fixed_price", "price", "description"],
                     dtype={"bid_code": str, "description": str}, quoting=3)
    ln["description"] = ln["description"].fillna("")

    keys = ln[["bid_code", "description"]].drop_duplicates().reset_index(drop=True)
    print(f"unique (bid_code, description) pairs: {len(keys)}")

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL, device="cpu")
    texts = (keys["bid_code"] + " " + keys["description"]).tolist()
    emb = model.encode(texts, batch_size=64, convert_to_numpy=True,
                       normalize_embeddings=True, show_progress_bar=False)
    print(f"embeddings: {emb.shape} {emb.dtype}")

    np.save(os.path.join(DATA_DIR, "desc_emb.npy"), emb.astype(np.float32))
    keys.to_csv(os.path.join(DATA_DIR, "desc_keys.tsv"), sep="\t",
                index=False, header=False)
    print("wrote desc_emb.npy and desc_keys.tsv")


if __name__ == "__main__":
    main()
