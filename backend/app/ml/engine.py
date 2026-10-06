"""AI / ML engine.

Implements the models described in the capstone ML Model Documentation
(Deliverable 12) and GenAI Design Document (Deliverable 13), in a fully
offline, dependency-light way so the project runs without external LLM keys:

  * TicketClassifier  — TF-IDF + Logistic Regression (multi-class)         [FR-004]
  * SentimentScorer   — lexicon-based polarity scoring                     [FR-005]
  * ChurnModel        — logistic-style heuristic over customer features    [FR-008]
  * KnowledgeAssistant— TF-IDF retrieval over KB chunks (RAG retrieval)    [FR-003]

In production the GenAI assistant's retrieval step feeds an LLM (see
GenAI Design Document); here the top retrieved chunk is returned directly as a
grounded, citation-bearing suggested reply, so the flow is identical minus the
generation call.
"""
from __future__ import annotations
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity

from app.ml.training_data import TRAINING_TICKETS, SENTIMENT_LEXICON


# ---------------------------------------------------------------------------
# 1. Ticket classification  (FR-004)
# ---------------------------------------------------------------------------
class TicketClassifier:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, stop_words="english")
        self.model = LogisticRegression(max_iter=1000)
        self.labels: list[str] = []
        self._fitted = False

    def fit(self):
        texts = [t["text"] for t in TRAINING_TICKETS]
        labels = [t["category"] for t in TRAINING_TICKETS]
        X = self.vectorizer.fit_transform(texts)
        self.model.fit(X, labels)
        self.labels = sorted(set(labels))
        self._fitted = True
        return self

    def predict(self, text: str) -> tuple[str, float]:
        if not self._fitted:
            self.fit()
        X = self.vectorizer.transform([text])
        proba = self.model.predict_proba(X)[0]
        idx = int(np.argmax(proba))
        return self.model.classes_[idx], float(proba[idx])


# ---------------------------------------------------------------------------
# 2. Sentiment analysis  (FR-005)
# ---------------------------------------------------------------------------
class SentimentScorer:
    _token = re.compile(r"[a-z']+")

    def score(self, text: str) -> tuple[str, float]:
        tokens = self._token.findall(text.lower())
        if not tokens:
            return "neutral", 0.0
        total = sum(SENTIMENT_LEXICON.get(tok, 0) for tok in tokens)
        # normalise to -1..1 by hits, not total token count, so signal isn't diluted
        hits = sum(1 for tok in tokens if tok in SENTIMENT_LEXICON) or 1
        score = max(-1.0, min(1.0, total / hits))
        if score > 0.15:
            label = "positive"
        elif score < -0.15:
            label = "negative"
        else:
            label = "neutral"
        return label, round(score, 3)


# ---------------------------------------------------------------------------
# 3. Churn prediction  (FR-008)
# ---------------------------------------------------------------------------
class ChurnModel:
    """Transparent logistic-style score over interpretable features.

    Features: open-ticket count, negative-sentiment ratio, avg resolution hours,
    tenure (months), segment weight. Documented for explainability per the
    Responsible-AI section of the ML Model Documentation.
    """
    def score(
        self,
        open_tickets: int,
        neg_ratio: float,
        avg_resolution_hours: float,
        tenure_months: int,
        segment: str,
    ) -> float:
        seg_w = {"Standard": 0.0, "Premium": -0.3, "Wealth": -0.5}.get(segment, 0.0)
        z = (
            -1.2
            + 0.55 * open_tickets
            + 2.4 * neg_ratio
            + 0.04 * avg_resolution_hours
            - 0.02 * tenure_months
            + seg_w
        )
        prob = 1.0 / (1.0 + np.exp(-z))
        return float(round(prob, 3))


# ---------------------------------------------------------------------------
# 4. Knowledge assistant — RAG retrieval  (FR-003)
# ---------------------------------------------------------------------------
def _light_stem(word: str) -> str:
    """Very small suffix stripper so "charged"/"charges" match "charge"."""
    for suffix in ("ing", "ed", "es", "s", "e"):
        if len(word) > 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _kb_analyzer(text: str) -> list[str]:
    return [_light_stem(w) for w in re.findall(r"[a-z0-9]+", text.lower())
            if w not in ENGLISH_STOP_WORDS]


class KnowledgeAssistant:
    """TF-IDF retrieval over KB chunks. Returns the best chunk + a citation.

    Mirrors the RAG flow in the GenAI Design Document:
        embed query -> similarity search -> assemble grounded answer + source.
    Below a confidence floor the assistant escalates to a human agent instead
    of guessing (guardrail from the GenAI governance section).
    """
    ESCALATE_THRESHOLD = 0.12

    def __init__(self):
        # Stemmed, sub-linear TF-IDF: "charged twice" now retrieves the
        # "Disputing an incorrect charge" article instead of a card article.
        self.vectorizer = TfidfVectorizer(analyzer=_kb_analyzer, sublinear_tf=True)
        self.matrix = None
        self.chunks: list[dict] = []

    def index(self, chunks: list[dict]):
        """chunks: [{chunk_id, content, article_id, title}]"""
        self.chunks = chunks
        if not chunks:
            self.matrix = None
            return self
        self.matrix = self.vectorizer.fit_transform([c["content"] for c in chunks])
        return self

    def answer(self, query: str) -> dict:
        if self.matrix is None or not self.chunks:
            return {"escalate": True, "answer": None, "source": None, "confidence": 0.0}
        q = self.vectorizer.transform([query])
        sims = cosine_similarity(q, self.matrix)[0]
        best = int(np.argmax(sims))
        confidence = float(sims[best])
        if confidence < self.ESCALATE_THRESHOLD:
            return {"escalate": True, "answer": None, "source": None, "confidence": round(confidence, 3)}
        chunk = self.chunks[best]
        return {
            "escalate": False,
            "answer": chunk["content"],
            "source": {"article_id": chunk["article_id"], "title": chunk["title"]},
            "confidence": round(confidence, 3),
        }


# Singletons reused across requests (trained once at startup).
classifier = TicketClassifier()
sentiment = SentimentScorer()
churn = ChurnModel()
assistant = KnowledgeAssistant()
