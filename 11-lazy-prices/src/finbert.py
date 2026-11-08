"""FinBERT (ProsusAI/finbert) tone of every MD&A sentence; firm-year score = mean of P(positive) − P(negative).

Sentences repeated across years are scored once (the model is deterministic, so the result is identical).
Progress is checkpointed to data/raw_10k/finbert_scores.json so the run can resume.

    python src/finbert.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
SENT = ROOT / "data" / "raw_10k" / "mda_sentences.json"
CKPT = ROOT / "data" / "raw_10k" / "finbert_scores.json"
OUT = ROOT / "data" / "finbert_mda.csv"
BATCH, MAXLEN = 64, 256


def main():
    torch.set_num_threads(4)
    tok = AutoTokenizer.from_pretrained("ProsusAI/finbert")
    model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert").eval()
    lab = {v: k for k, v in model.config.id2label.items()}
    S = json.load(open(SENT))
    uniq = sorted({s for v in S.values() for s in v}, key=lambda s: len(s))   # length-sorted batches minimise padding
    done = json.load(open(CKPT)) if CKPT.exists() else {}
    todo = [s for s in uniq if s not in done]
    print(f"{len(uniq):,} unique sentences, {len(todo):,} to score", flush=True)
    t0 = time.time()
    with torch.inference_mode():
        for i in range(0, len(todo), BATCH):
            b = todo[i:i + BATCH]
            enc = tok(b, padding=True, truncation=True, max_length=MAXLEN, return_tensors="pt")
            p = model(**enc).logits.softmax(-1).numpy()
            for s, row in zip(b, p):
                done[s] = float(row[lab["positive"]] - row[lab["negative"]])
            if (i // BATCH) % 200 == 0 or i + BATCH >= len(todo):
                json.dump(done, open(CKPT, "w"))
                rate = (i + len(b)) / (time.time() - t0)
                print(f"{i + len(b):,}/{len(todo):,}  {rate:.1f} sent/s", flush=True)
    rows = [{"ticker": k.split("|")[0], "fy": int(k.split("|")[1]), "finbert_mda": float(np.mean([done[s] for s in v])) if v else np.nan,
             "n_sent": len(v)} for k, v in S.items()]
    pd.DataFrame(rows).sort_values(["ticker", "fy"]).to_csv(OUT, index=False)
    print("wrote", OUT)


if __name__ == "__main__":
    sys.exit(main())
