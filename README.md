# Backoffice Ebook

Un backoffice pour la gestion et la validation d'ebooks avec une architecture hexagonale.

## Prérequis

- Python 3.11
- PostgreSQL
- OpenAI API Key

## Installation

1. Cloner le repository
2. Créer un environnement virtuel :
```bash
python -m venv venv
source venv/bin/activate  # Sur Unix
# ou
.\venv\Scripts\activate  # Sur Windows
```

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. Copier le fichier .env.example en .env et configurer les variables d'environnement :
```bash
cp .env.example .env
```

5. Configurer la base de données PostgreSQL et mettre à jour l'URL de connexion dans le fichier .env

## Lancement

```bash
uvicorn main:app --reload
```

L'application sera accessible à l'adresse : http://localhost:8000

## Documentation API

La documentation Swagger est disponible à l'adresse : http://localhost:8000/docs

## Fonctionnalités

- Authentification admin
- Dashboard avec statistiques
- Liste des ebooks à valider
- Visualisation des ebooks
- Chat avec LLM pour les retours
- Validation des ebooks 