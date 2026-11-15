from app.main import Base,engine
# LAB ONLY: replace with Alembic migration plan for production.
Base.metadata.create_all(bind=engine)
