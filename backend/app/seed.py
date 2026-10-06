"""Seed the database with demo data and index the knowledge base.

Idempotent: running twice will not duplicate rows. Invoked automatically at
startup (if the DB is empty) and runnable manually:  python -m app.seed
"""
import time
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine, Base
from app.db import models
from app.core import security
from app.ml.engine import classifier, sentiment, assistant


KB_ARTICLES = [
    ("Resetting your password",
     "To reset your password, open the login page and select Forgot Password. "
     "Enter your registered email and follow the secure reset link sent to your inbox. "
     "If the link does not arrive within 10 minutes, check your spam folder or contact support."),
    ("Blocking a lost or stolen card",
     "If your card is lost or stolen, block it immediately from the mobile app under "
     "Cards > Manage > Block Card, or call the 24x7 helpline. A replacement card is "
     "issued within 5 to 7 working days to your registered address."),
    ("Failed fund transfer with amount debited",
     "If a fund transfer failed but the amount was debited, the amount is usually "
     "auto-reversed within 3 to 5 working days. If it is not reversed, raise a ticket "
     "with the transaction reference and we will investigate with the beneficiary bank."),
    ("Disputing an incorrect charge",
     "To dispute an incorrect or duplicate charge, raise a ticket with the statement "
     "date and amount. Disputed transactions are investigated within 7 working days and "
     "provisional credit may be applied for eligible cases."),
    ("Increasing your credit card limit",
     "You can request a credit card limit increase from the app under Cards > Limit. "
     "Eligibility depends on your repayment history and income documents. Decisions are "
     "typically communicated within 2 working days."),
    ("Updating KYC details",
     "To update your KYC documents, go to Profile > KYC and upload a valid identity and "
     "address proof. Updated documents are verified within 2 working days, after which "
     "your account status is refreshed."),
    ("Loan EMI and repayment",
     "Your loan EMI is auto-debited on the scheduled date each month. To reschedule the "
     "repayment date or check your outstanding balance, open Loans > Manage. If an EMI is "
     "deducted twice, the extra amount is reversed within 5 working days."),
    ("Unlocking your account",
     "Accounts are temporarily locked after multiple failed login attempts as a security "
     "measure. Wait 30 minutes and retry, or reset your password to unlock immediately. "
     "Two-factor authentication must be completed to restore access."),
]


def seed(db: Session):
    # ---- roles ----
    role_names = ["admin", "agent", "manager", "executive", "customer"]
    roles = {}
    for rn in role_names:
        r = db.query(models.Role).filter(models.Role.name == rn).first()
        if not r:
            r = models.Role(name=rn)
            db.add(r)
            db.flush()
        roles[rn] = r

    # ---- internal users ----
    staff = [
        ("Admin User", "admin@abcfin.com", "admin123", "admin"),
        ("Arjun Agent", "agent@abcfin.com", "agent123", "agent"),
        ("Meera Manager", "manager@abcfin.com", "manager123", "manager"),
        ("Esha Executive", "exec@abcfin.com", "exec123", "executive"),
    ]
    for name, email, pw, role in staff:
        if not db.query(models.Agent).filter(models.Agent.email == email).first():
            db.add(models.Agent(name=name, email=email,
                                password_hash=security.hash_password(pw),
                                role_id=roles[role].role_id))

    # ---- customers ----
    customers_spec = [
        ("Rahul Sharma", "rahul@example.com", "Standard", 8),
        ("Priya Nair", "priya@example.com", "Premium", 36),
        ("Imran Khan", "imran@example.com", "Wealth", 60),
        ("Sunita Rao", "sunita@example.com", "Standard", 4),
    ]
    cust = {}
    for name, email, seg, tenure in customers_spec:
        c = db.query(models.Customer).filter(models.Customer.email == email).first()
        if not c:
            c = models.Customer(name=name, email=email, segment=seg, tenure_months=tenure,
                                password_hash=security.hash_password("customer123"))
            db.add(c)
            db.flush()
        cust[email] = c

    # ---- categories (also created on demand by the classifier) ----
    for cn in ["Billing", "Account Access", "Cards", "Transfers", "Loans", "General"]:
        if not db.query(models.Category).filter(models.Category.name == cn).first():
            db.add(models.Category(name=cn))
    db.flush()

    # ---- sample tickets (only if none exist) ----
    if db.query(models.Ticket).count() == 0:
        samples = [
            ("rahul@example.com", "Double charge on my card",
             "I was charged twice for my subscription this month and it is very frustrating.", True),
            ("priya@example.com", "Cannot log in",
             "I forgot my password and the reset link does not work. Please help quickly.", False),
            ("imran@example.com", "International transfer pending",
             "My international wire transfer has been pending for three days. Thanks for checking.", False),
            ("sunita@example.com", "Lost my debit card",
             "I lost my debit card and need to block it immediately. This is urgent.", True),
            ("rahul@example.com", "Loan EMI deducted twice",
             "My loan EMI was deducted twice this month, please reverse the extra amount.", False),
        ]
        def _cat(db, name):
            return db.query(models.Category).filter(models.Category.name == name).first()
        for email, subject, body, close in samples:
            text = f"{subject}. {body}"
            label, conf = classifier.predict(text)
            slabel, sscore = sentiment.score(text)
            cat = _cat(db, label)
            t = models.Ticket(
                customer_id=cust[email].customer_id,
                category_id=cat.category_id if cat else None,
                subject=subject, body=body, status="closed" if close else "open",
                priority="high" if slabel == "negative" else "medium",
                classification_confidence=round(conf, 3),
                created_at=datetime.now(timezone.utc) - timedelta(days=3),
                resolved_at=(datetime.now(timezone.utc) - timedelta(days=1)) if close else None,
            )
            db.add(t)
            db.flush()
            db.add(models.Message(ticket_id=t.ticket_id, sender_type="customer",
                                  sender_name=cust[email].name, body=body))
            db.add(models.Sentiment(ticket_id=t.ticket_id, label=slabel, score=sscore))

    # ---- knowledge base + RAG chunks ----
    if db.query(models.KBArticle).count() == 0:
        for title, body in KB_ARTICLES:
            art = models.KBArticle(title=title, body=body)
            db.add(art)
            db.flush()
            # naive chunking: whole article is one chunk (articles are short here)
            db.add(models.RAGChunk(article_id=art.article_id, content=f"{title}. {body}"))

    db.commit()


def index_knowledge_base(db: Session):
    rows = (db.query(models.RAGChunk, models.KBArticle)
            .join(models.KBArticle, models.RAGChunk.article_id == models.KBArticle.article_id)
            .all())
    chunks = [{"chunk_id": ch.chunk_id, "content": ch.content,
               "article_id": art.article_id, "title": art.title}
              for ch, art in rows]
    assistant.index(chunks)


def _log(message: str):
    print(f"[startup] {message}", flush=True)


def wait_for_database(timeout_seconds: int = 180, interval_seconds: float = 2.0):
    """Block until the database accepts connections.

    In Docker the backend can start a moment before PostgreSQL is ready (for
    example while it initialises on first boot). Without this wait the app
    would crash at startup with "connection refused".
    """
    deadline = time.monotonic() + timeout_seconds
    target = engine.url.render_as_string(hide_password=True)
    _log(f"connecting to database {target}")
    while True:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            _log("database connected")
            return
        except OperationalError as exc:
            if time.monotonic() >= deadline:
                _log(f"giving up: database still unreachable after {timeout_seconds}s")
                raise
            reason = str(getattr(exc, "orig", exc)).strip().splitlines()[0][:160]
            print(f"Database not ready yet ({reason}); retrying in "
                  f"{interval_seconds:g}s...", flush=True)
            time.sleep(interval_seconds)


def init_and_seed():
    started = time.monotonic()
    wait_for_database()
    Base.metadata.create_all(bind=engine)
    _log("tables ready")
    classifier.fit()
    _log("ticket classifier trained")
    db = SessionLocal()
    try:
        seed(db)
        _log("demo data ready")
        index_knowledge_base(db)
        _log("knowledge base indexed")
    finally:
        db.close()
    _log(f"complete in {time.monotonic() - started:.1f}s")


if __name__ == "__main__":
    init_and_seed()
    print("Database seeded and knowledge base indexed.")
