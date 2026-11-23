"""Extractive summarization by sentence scoring.
Score(sentence) = sum(word frequency of its non-stop words) / sqrt(#words) + early-position bonus.
The top-n sentences are returned in original order. Time: O(S*W + S log S)."""
import math, re
from collections import Counter
from algorithms import tokenize

def summarize(text, n=2):
    sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\'])', text or "") if len(s.strip()) > 20]
    if len(sents) <= n:
        return (text or "").strip()
    freq = Counter(w for s in sents for w in tokenize(s))
    def score(i):
        toks = tokenize(sents[i])
        return (sum(freq[w] for w in toks) / math.sqrt(len(toks) or 1)) + (1.5 if i == 0 else 0) / (1 + i * 0.3)
    top = sorted(sorted(range(len(sents)), key=score, reverse=True)[:n])
    return " ".join(sents[i] for i in top)
