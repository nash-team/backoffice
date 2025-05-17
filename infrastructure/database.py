from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
import os
import logging

logger = logging.getLogger(__name__)

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://blacksun:password@127.0.0.1:5432/backoffice"
)

# Configuration du pool de connexions pour la scalabilité
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,  # Nombre de connexions simultanées
    max_overflow=10,  # Connexions supplémentaires en cas de pic
    pool_timeout=30,  # Timeout pour obtenir une connexion
    pool_recycle=1800,  # Recyclage des connexions après 30 minutes
    echo=True  # Log des requêtes SQL en développement
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        logger.debug("Nouvelle connexion à la base de données établie")
        yield db
    except Exception as e:
        logger.error(f"Erreur de base de données: {str(e)}")
        raise
    finally:
        logger.debug("Fermeture de la connexion à la base de données")
        db.close() 