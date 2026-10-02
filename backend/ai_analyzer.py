"""
ai_analyzer.py
--------------
The "AI" core of the Secure Chat Analyser.

For each chat message it produces:
  1. Sentiment analysis        -> polarity score (-1..1) + label (positive/neutral/negative)
  2. Toxicity / abuse scoring  -> lexicon-based severity score (0..1) + matched terms
  3. Sensitive-info detection  -> regex scan for emails, phone numbers, card numbers, links
  4. A combined risk level     -> SAFE / LOW / MEDIUM / HIGH

Design notes for your report:
- Sentiment uses TextBlob (a pattern-based analyzer) - lightweight, no GPU/model download.
- Toxicity uses a weighted keyword lexicon rather than a trained transformer model,
  which keeps the project runnable on any laptop with no internet-dependent model
  downloads. This is clearly documented as an area you can upgrade
  (e.g. swap in HuggingFace's `unitary/toxic-bert` or a scikit-learn classifier
  trained on the Jigsaw Toxic Comments dataset) for the "future scope" section.
- Sensitive-info detection uses regex, a standard technique in DLP
  (Data Loss Prevention) tools, to demonstrate the "secure" half of the project.
"""

import re
from textblob import TextBlob


# --- Lexicon-based toxicity detector -----------------------------------
# Each term maps to a severity weight (0..1). This is intentionally simple
# and transparent so you can explain exactly how a score was produced -
# a common requirement in PBL vivas.
TOXIC_LEXICON = {
    "idiot": 0.5, "stupid": 0.4, "dumb": 0.3, "hate": 0.4, "kill": 0.8,
    "shut up": 0.4, "loser": 0.4, "worthless": 0.6, "ugly": 0.3,
    "trash": 0.3, "die": 0.7, "attack": 0.5, "threat": 0.6,
    "moron": 0.5, "pathetic": 0.4, "disgusting": 0.3, "scam": 0.5,
    "fraud": 0.5, "abuse": 0.5, "violence": 0.6,
    "murder": 0.9, "assault": 0.8, "suicide": 0.9, "terrorist": 0.9,
    "rape": 0.9, "bomb": 0.8, "weapon": 0.6, "harm": 0.5,
    "racist": 0.6, "bully": 0.5, "harass": 0.6, "blackmail": 0.7,
}

# Regex patterns for sensitive information that shouldn't be shared in chat
SENSITIVE_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b(?:\+?\d{1,3}[- ]?)?\d{10}\b"),
    "card_number": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "url": re.compile(r"https?://[^\s]+|www\.[^\s]+"),
}


class ChatAnalyzer:
    def __init__(self, toxicity_threshold: float = 0.4, negative_sentiment_threshold: float = -0.4):
        self.toxicity_threshold = toxicity_threshold
        self.negative_sentiment_threshold = negative_sentiment_threshold

    # 1. Sentiment -------------------------------------------------------
    def analyze_sentiment(self, text: str) -> dict:
        blob = TextBlob(text)
        polarity = round(blob.sentiment.polarity, 3)   # -1 (neg) .. 1 (pos)
        subjectivity = round(blob.sentiment.subjectivity, 3)  # 0 (fact) .. 1 (opinion)

        if polarity > 0.15:
            label = "positive"
        elif polarity < -0.15:
            label = "negative"
        else:
            label = "neutral"

        return {"polarity": polarity, "subjectivity": subjectivity, "label": label}

    # 2. Toxicity ---------------------------------------------------------
    def analyze_toxicity(self, text: str) -> dict:
        lowered = text.lower()
        matched = []
        score = 0.0
        for term, weight in TOXIC_LEXICON.items():
            if term in lowered:
                matched.append(term)
                score = max(score, weight)  # take the worst single match

        # small boost if multiple toxic terms appear together
        if len(matched) > 1:
            score = min(1.0, score + 0.1 * (len(matched) - 1))

        return {
            "score": round(score, 3),
            "flagged": score >= self.toxicity_threshold,
            "matched_terms": matched,
        }

    # 3. Sensitive info -----------------------------------------------------
    def detect_sensitive_info(self, text: str) -> dict:
        found = {}
        for label, pattern in SENSITIVE_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                found[label] = matches
        return {"has_sensitive_info": bool(found), "details": found}

    # 4. Combine everything into one risk verdict ---------------------------
    def get_risk_level(self, sentiment: dict, toxicity: dict, sensitive: dict) -> str:
        if toxicity["score"] >= 0.7 or "card_number" in sensitive["details"]:
            return "HIGH"
        if toxicity["flagged"] or sensitive["has_sensitive_info"]:
            return "MEDIUM"
        if sentiment["polarity"] <= self.negative_sentiment_threshold:
            return "LOW"
        return "SAFE"

    def analyze(self, text: str) -> dict:
        sentiment = self.analyze_sentiment(text)
        toxicity = self.analyze_toxicity(text)
        sensitive = self.detect_sensitive_info(text)
        risk = self.get_risk_level(sentiment, toxicity, sensitive)

        return {
            "sentiment": sentiment,
            "toxicity": toxicity,
            "sensitive_info": sensitive,
            "risk_level": risk,
        }


if __name__ == "__main__":
    analyzer = ChatAnalyzer()
    samples = [
        "Hey, are we still meeting for lunch tomorrow?",
        "You are such an idiot, I hate talking to you",
        "Call me at 9876543210 or email me at test@example.com",
        "I might just die if this project doesn't work",
    ]
    for s in samples:
        print(s, "->", analyzer.analyze(s))