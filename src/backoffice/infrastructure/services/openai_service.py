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
                model="gpt-3.5-turbo",
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
                model="gpt-3.5-turbo",
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
