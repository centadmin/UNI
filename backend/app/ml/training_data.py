"""Seed training data for the offline ML models.

In production these are replaced by historical labelled tickets (see the
ML Model Documentation data-pipeline section). Kept small and readable here so
the classifier trains in milliseconds at startup.
"""

# Labelled tickets for the TF-IDF + Logistic Regression classifier.
TRAINING_TICKETS = [
    # Billing
    {"text": "I was charged twice for my monthly subscription fee", "category": "Billing"},
    {"text": "There is an incorrect charge on my credit card statement", "category": "Billing"},
    {"text": "Refund not received for the cancelled transaction", "category": "Billing"},
    {"text": "Why was an extra processing fee deducted from my account", "category": "Billing"},
    {"text": "My invoice amount looks wrong this month", "category": "Billing"},
    {"text": "I want a breakdown of the charges on my loan account", "category": "Billing"},
    # Account access
    {"text": "I cannot log in to my online banking account", "category": "Account Access"},
    {"text": "Forgot my password and the reset link does not work", "category": "Account Access"},
    {"text": "My account is locked after too many login attempts", "category": "Account Access"},
    {"text": "Two factor authentication code is not arriving on my phone", "category": "Account Access"},
    {"text": "How do I reset my net banking username", "category": "Account Access"},
    {"text": "I am unable to access the mobile app after the update", "category": "Account Access"},
    # Cards
    {"text": "My debit card was declined at the store", "category": "Cards"},
    {"text": "I need to block my lost credit card immediately", "category": "Cards"},
    {"text": "How do I increase my credit card limit", "category": "Cards"},
    {"text": "My new card has not been delivered yet", "category": "Cards"},
    {"text": "International transactions are blocked on my card", "category": "Cards"},
    # Transfers / payments
    {"text": "My fund transfer failed but the amount was debited", "category": "Transfers"},
    {"text": "NEFT payment to a beneficiary is still pending", "category": "Transfers"},
    {"text": "How long does an international wire transfer take", "category": "Transfers"},
    {"text": "I sent money to the wrong account number", "category": "Transfers"},
    {"text": "UPI payment is showing as failed but money was deducted", "category": "Transfers"},
    # Loans
    {"text": "What is the interest rate on a personal loan", "category": "Loans"},
    {"text": "I want to know my home loan outstanding balance", "category": "Loans"},
    {"text": "How do I apply for a top up on my existing loan", "category": "Loans"},
    {"text": "My EMI was deducted twice this month", "category": "Loans"},
    {"text": "Request to reschedule my loan repayment date", "category": "Loans"},
    # General / complaints
    {"text": "The customer service wait time is too long", "category": "General"},
    {"text": "I want to update my registered email address", "category": "General"},
    {"text": "How do I update my KYC documents", "category": "General"},
    {"text": "I would like to close my savings account", "category": "General"},
]

# Simple polarity lexicon for sentiment scoring.
SENTIMENT_LEXICON = {
    # negative
    "not": -0.4, "no": -0.3, "never": -0.6, "failed": -0.8, "fail": -0.7,
    "wrong": -0.7, "incorrect": -0.7, "declined": -0.6, "locked": -0.5,
    "lost": -0.5, "delayed": -0.6, "late": -0.5, "angry": -0.9, "frustrated": -0.9,
    "frustrating": -0.9, "terrible": -1.0, "worst": -1.0, "poor": -0.8, "bad": -0.7,
    "unable": -0.6, "cannot": -0.5, "blocked": -0.5, "double": -0.4, "twice": -0.4,
    "unacceptable": -1.0, "disappointed": -0.8, "complaint": -0.6, "issue": -0.4,
    "problem": -0.5, "error": -0.6, "stuck": -0.5, "pending": -0.3, "still": -0.2,
    # positive
    "thanks": 0.8, "thank": 0.8, "great": 0.9, "good": 0.7, "excellent": 1.0,
    "happy": 0.9, "resolved": 0.8, "appreciate": 0.9, "helpful": 0.8, "quick": 0.6,
    "fast": 0.6, "love": 0.9, "perfect": 1.0, "satisfied": 0.8, "smooth": 0.6,
}
