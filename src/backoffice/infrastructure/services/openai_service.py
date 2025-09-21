import asyncio
import logging
import os

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for OpenAI API integration"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=self.api_key)

    async def generate_ebook_json(self, prompt: str) -> dict[str, str]:
        """Generate ebook content in structured JSON format"""
        try:
            if not self.client:
                # Fallback to mock generation if no API key
                logger.info("No OpenAI API key, using mock JSON generation")
                return await self._mock_generate_json(prompt)

            # Generate ebook content using OpenAI API
            logger.info("Generating ebook JSON structure using OpenAI API")

            # Create a structured prompt for JSON ebook generation
            system_prompt = """Tu es un expert en rédaction d'ebooks éducatifs.
Tu dois générer un contenu structuré en JSON basé sur le prompt de l'utilisateur.
Le JSON doit strictement suivre ce format :

{
  "meta": {
    "title": "Titre de l'ebook",
    "subtitle": "Sous-titre optionnel",
    "author": "Assistant IA",
    "language": "fr",
    "genre": "genre approprié",
    "trim": "A4",
    "cover_color": "#couleur-hex",
    "engine": "weasyprint"
  },
  "cover": {
    "title": "Titre de couverture",
    "subtitle": "Sous-titre de couverture",
    "tagline": "Phrase accrocheuse",
    "image_url": null
  },
  "toc": true,
  "sections": [
    {"type": "chapter", "title": "Chapitre 1 — Titre",
     "content_md": "Contenu en markdown du chapitre..."},
    {"type": "chapter", "title": "Chapitre 2 — Titre",
     "content_md": "Contenu en markdown du chapitre..."}
  ],
  "back_cover": {
    "blurb": "Résumé de l'ebook...",
    "about_author": "À propos de l'auteur..."
  }
}

IMPORTANT:
- Chaque "chapter" doit être un chapitre complet avec tout son contenu
- Le content_md contient TOUT le texte du chapitre (pas juste le titre)
- Assure-toi que chaque chapitre soit substantiel et autonome
- Réponds UNIQUEMENT avec le JSON valide, sans préambule ni explication"""

            user_prompt = f"""Génère un ebook complet sur le sujet suivant: {prompt}

L'ebook doit contenir:
- 3 à 5 chapitres substantiels et bien développés
- Chaque chapitre doit être complet avec introduction, développement et conclusion
- Contenu éducatif et adapté au sujet
- Style engageant et accessible

Réponds UNIQUEMENT avec le JSON structuré."""

            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4000,
                temperature=0.7,
            )

            json_content = response.choices[0].message.content.strip()

            # Validate JSON
            try:
                import json

                json.loads(json_content)
            except json.JSONDecodeError:
                logger.warning("OpenAI returned invalid JSON, using fallback")
                return await self._mock_generate_json(prompt)

            return {"content": json_content}

        except Exception as e:
            logger.error(f"Error generating JSON with OpenAI: {str(e)}")
            # Fallback to mock on error
            return await self._mock_generate_json(prompt)

    async def generate_ebook_content(self, prompt: str) -> dict[str, str]:
        """Generate ebook content from prompt using OpenAI"""
        try:
            if not self.client:
                # Fallback to mock generation if no API key
                logger.info("No OpenAI API key, using mock generation")
                return await self._mock_generate_content(prompt)

            # Generate ebook content using OpenAI API
            logger.info("Generating ebook content using OpenAI API")

            # Create a structured prompt for ebook generation
            system_prompt = """Tu es un expert en rédaction d'ebooks éducatifs.
Tu dois générer un contenu complet et structuré basé sur le prompt de l'utilisateur.
Le contenu doit être informatif, bien organisé et adapté à un format ebook.
Réponds uniquement avec le contenu de l'ebook en markdown, sans préambule."""

            user_prompt = f"""Génère un ebook complet sur le sujet suivant: {prompt}

Le contenu doit inclure:
- Une introduction engageante
- Plusieurs chapitres bien structurés avec des sous-sections
- Des exemples pratiques et concrets
- Une conclusion
- Le tout formaté en markdown

Assure-toi que le contenu soit substantiel (au moins 2000 mots) et éducatif."""

            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4000,
                temperature=0.7,
            )

            content = response.choices[0].message.content

            # Generate title from the prompt
            title_prompt = (
                f"Génère un titre accrocheur et professionnel pour un ebook sur: {prompt}. "
                "Réponds uniquement avec le titre, sans guillemets."
            )

            title_response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": title_prompt}],
                max_tokens=50,
                temperature=0.5,
            )

            title = title_response.choices[0].message.content.strip()

            return {"title": title, "content": content, "author": "Assistant IA"}

        except Exception as e:
            logger.error(f"Error generating content with OpenAI: {str(e)}")
            # Fallback to mock on error
            return await self._mock_generate_content(prompt)

    async def _mock_generate_content(self, prompt: str) -> dict[str, str]:
        """Mock content generation for testing"""
        # Simulate processing time
        await asyncio.sleep(0.5)

        # Extract keywords from prompt for title generation
        words = prompt.split()[:5]
        topic = " ".join(words).title()

        # Generate mock content based on prompt
        content = f"""## Introduction

Ce guide a été généré à partir de votre demande : "{prompt}"

## Chapitre 1: Fondamentaux

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor
incididunt ut labore et dolore magna aliqua.

## Chapitre 2: Concepts Avancés

Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut
aliquip ex ea commodo consequat.

## Chapitre 3: Exemples Pratiques

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu
fugiat nulla pariatur.

## Conclusion

Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia
deserunt mollit anim id est laborum.

---

*Note: Ce contenu a été généré automatiquement et nécessite une révision.*
"""

        return {"title": f"Guide Pratique: {topic}", "content": content, "author": "Assistant IA"}

    async def _mock_generate_json(self, prompt: str) -> dict[str, str]:
        """Mock JSON content generation for testing"""
        await asyncio.sleep(0.5)

        # Extract keywords from prompt for title generation
        words = prompt.split()[:3]
        topic = " ".join(words).title()

        mock_json = {
            "meta": {
                "title": f"Guide Pratique : {topic}",
                "subtitle": "Un ebook généré automatiquement",
                "author": "Assistant IA",
                "language": "fr",
                "genre": "éducatif",
                "trim": "A4",
                "cover_color": "#2c3e50",
                "engine": "weasyprint",
            },
            "cover": {
                "title": f"Guide Pratique : {topic}",
                "subtitle": "Découverte et apprentissage",
                "tagline": f"Explorez le monde de {topic.lower()}",
                "image_url": None,
            },
            "toc": True,
            "sections": [
                {
                    "type": "chapter",
                    "title": "Chapitre 1 — Introduction",
                    "content_md": f"""Ce guide a été généré à partir de votre demande : "{prompt}"

## Présentation du sujet

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor
incididunt ut labore et dolore magna aliqua.

## Objectifs de ce chapitre

- Comprendre les bases
- Découvrir les concepts clés
- Préparer la suite de l'apprentissage

Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.""",
                },
                {
                    "type": "chapter",
                    "title": "Chapitre 2 — Concepts Fondamentaux",
                    "content_md": """## Les bases essentielles

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore
eu fugiat nulla pariatur.

### Point important 1

Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia
deserunt mollit anim id est laborum.

### Point important 2

Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium
doloremque laudantium.""",
                },
                {
                    "type": "chapter",
                    "title": "Chapitre 3 — Applications Pratiques",
                    "content_md": """## Mise en pratique

Totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi
architecto beatae vitae dicta sunt explicabo.

### Exemple concret

Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit.

### Exercices

1. Premier exercice pratique
2. Deuxième exercice d'application
3. Cas d'étude complet

## Conclusion du chapitre

At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis.""",
                },
            ],
            "back_cover": {
                "blurb": (
                    f"Ce guide pratique vous accompagne dans la découverte de {topic.lower()}. "
                    "Avec des explications claires et des exemples concrets, vous maîtriserez "
                    "rapidement les concepts essentiels."
                ),
                "about_author": (
                    "L'Assistant IA est spécialisé dans la création de contenus éducatifs "
                    "accessibles et pédagogiques."
                ),
            },
        }

        import json

        return {"content": json.dumps(mock_json, ensure_ascii=False, indent=2)}
