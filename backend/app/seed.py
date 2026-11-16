"""Cria usuários de demo.  Uso:  python -m app.seed"""
from sqlalchemy import select

from . import models
from .db import Base, SessionLocal, engine
from .passwords import hash_password

PASSWORD = "demo1234"
USERS = [
    ("admin@astrokatu.dev", "Admin Demo", "admin"),
    ("clinico@astrokatu.dev", "Dra. Helena (clínica)", "clinician"),
    ("astro1@astrokatu.dev", "Astronauta Ana", "astronaut"),
    ("astro2@astrokatu.dev", "Astronauta Bruno", "astronaut"),
]


def main():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        by_email = {}
        for email, name, role in USERS:
            u = db.scalar(select(models.User).where(models.User.email == email))
            if not u:
                u = models.User(email=email, name=name, role=role, password_hash=hash_password(PASSWORD))
                db.add(u)
                db.flush()
            by_email[email] = u
        clin = by_email["clinico@astrokatu.dev"]
        for email in ("astro1@astrokatu.dev", "astro2@astrokatu.dev"):
            a = by_email[email]
            if not db.scalar(select(models.Assignment).where(
                    models.Assignment.clinician_id == clin.id, models.Assignment.astronaut_id == a.id)):
                db.add(models.Assignment(clinician_id=clin.id, astronaut_id=a.id))
        db.commit()
        print(f"Senha de todos: {PASSWORD}")
        for email, u in by_email.items():
            print(f"  {u.role:<10} {email:<26} id={u.id}")


if __name__ == "__main__":
    main()
