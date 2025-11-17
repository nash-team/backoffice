"""OpenRouter API service for multi-model LLM access."""

import logging
import os

from openai import AsyncOpenAI

from backoffice.features.ebook.shared.domain.entities.ebook import EbookConfig

logger = logging.getLogger(__name__)


class OpenRouterService:
    """Service for OpenRouter API integration - supports multiple LLM providers."""

    def __init__(self, model: str | None = None):
        """Initialize OpenRouter service.

        Args:
            model: Specific model to use (e.g., "anthropic/claude-3.5-sonnet")
                   If None, will use LLM_TEXT_MODEL from environment
        """
        self.api_key = os.getenv("LLM_API_KEY")
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = model or os.getenv("LLM_TEXT_MODEL", "anthropic/claude-3.5-sonnet")

        if not self.api_key:
            logger.warning("LLM_API_KEY not found in environment variables")
            self.client = None
        else:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            logger.info(f"OpenRouterService initialized with model: {self.model}")

    def _handle_openrouter_error(self, error: Exception, operation: str) -> None:
        """Handle OpenRouter API errors with specific error codes.

        Args:
            error: The exception that occurred
            operation: Description of the operation that failed (for error messages)

        Raises:
            ValueError: With user-friendly error message based on error type
        """
        logger.error(f"Error during {operation} with OpenRouter: {str(error)}")
        error_msg = str(error)

        # Check for specific OpenRouter error codes
        if (
            "402" in error_msg
            or "insufficient" in error_msg.lower()
            or "credits" in error_msg.lower()
        ):
            raise ValueError(
                "Crédits insuffisants sur votre compte OpenRouter. "
                "Veuillez ajouter des crédits sur https://openrouter.ai/settings/credits"
            ) from error
        elif "401" in error_msg or "unauthorized" in error_msg.lower():
            raise ValueError(
                "Clé API invalide. Veuillez vérifier votre LLM_API_KEY dans le fichier .env"
            ) from error
        elif "429" in error_msg or "rate limit" in error_msg.lower():
            raise ValueError(
                "Limite de requêtes atteinte. Veuillez réessayer dans quelques instants."
            ) from error
        else:
            raise ValueError(
                f"Erreur lors de la génération du contenu avec {self.model}: {error_msg}"
            ) from error

    async def generate_ebook_json(
        self, prompt: str, config: EbookConfig | None = None, theme_name: str | None = None
    ) -> dict[str, str]:
        """Generate ebook content in structured JSON format"""
        if not self.client:
            raise ValueError(
                "Configuration incomplète: la clé API LLM_API_KEY est manquante. "
                "Veuillez ajouter votre clé API dans le fichier .env"
            )

        try:
            # Generate ebook content using OpenRouter API
            logger.info(
                f"Generating ebook JSON structure using OpenRouter API (model: {self.model})"
            )

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
     "content": "Contenu en markdown du chapitre..."},
    {"type": "chapter", "title": "Chapitre 2 — Titre",
     "content": "Contenu en markdown du chapitre..."}
  ],
  "back_cover": {
    "blurb": "Résumé de l'ebook...",
    "about_author": "À propos de l'auteur..."
  }
}

IMPORTANT:
- Chaque "chapter" doit être un chapitre complet avec tout son contenu
- Le content contient TOUT le texte du chapitre (pas juste le titre)
- Assure-toi que chaque chapitre soit substantiel et autonome
- Réponds UNIQUEMENT avec le JSON valide, sans préambule ni explication"""

            # Build different prompts based on config type
            if config and config.number_of_pages:
                # Coloring book prompt - need +1 sections (first one becomes cover)
                total_sections_needed = config.number_of_pages + 1

                # Build theme-aware prompt
                if theme_name:
                    subject = f"livre de coloriage sur le thème des {theme_name.lower()}"
                    logger.info(f"Using theme-specific subject: {subject}")
                else:
                    subject = f"livre de coloriage sur le sujet suivant: {prompt}"

                pages_count = config.number_of_pages
                theme = theme_name or "demandé"
                user_prompt = f"""Génère un {subject}

Le livre doit contenir:
- Exactement {total_sections_needed} sections (1 pour la couverture + {pages_count} \
pour le coloriage)
- Chaque section doit avoir le type "image_page"
- Chaque titre doit être TRÈS COURT (3-5 mots max)
- Chaque contenu doit être UNE SEULE PHRASE SIMPLE décrivant l'image à colorier
- Pas de texte long, pas d'explication, juste la description visuelle pure
- IMPORTANT: Respecte le thème {theme} dans TOUTES les sections
- Exemple pour {theme}: title: "Pirate et trésor", \
content: "Un pirate avec un coffre au trésor"

IMPORTANT pour le meta.title et meta.subtitle:
- Titre ACCROCHEUR et COMMERCIAL pour la couverture
- Format: "Cahier de Coloriage [THÈME]" ou "[THÈME] à Colorier" ou \
"Aventures de [THÈME] à Colorier"
- UTILISE LE THÈME: {theme}
- Exemples: "Cahier de Coloriage {theme}", "{theme} à Colorier"
- Subtitle COMMERCIAL: "À partir de 4 ans" ou "{pages_count} Pages à Colorier" \
ou "Créativité et Détente"
- Le titre doit être VENDEUR et attirer les enfants/parents

Réponds UNIQUEMENT avec le JSON structuré."""
            else:
                # Story book prompt
                chapters_count = (
                    config.number_of_chapters if config and config.number_of_chapters else "3 à 5"
                )
                user_prompt = f"""Génère un ebook complet sur le sujet suivant: {prompt}

L'ebook doit contenir:
- Exactement {chapters_count} chapitres substantiels et bien développés
- Chaque chapitre doit être complet avec introduction, développement et conclusion
- Contenu éducatif et adapté au sujet
- Style engageant et accessible

Réponds UNIQUEMENT avec le JSON structuré."""

            # Call OpenRouter API with extra headers
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4000,
                temperature=0.7,
                extra_headers={
                    "HTTP-Referer": "https://ebook-generator.app",  # Optional but recommended
                    "X-Title": "Ebook Generator Backoffice",  # Optional but recommended
                },
            )

            json_content = response.choices[0].message.content.strip()

            # Validate JSON
            try:
                import json

                json.loads(json_content)
            except json.JSONDecodeError as json_err:
                logger.error("OpenRouter returned invalid JSON")
                raise ValueError(
                    f"Le modèle {self.model} a retourné un contenu JSON invalide. "
                    "Veuillez réessayer ou choisir un autre modèle."
                ) from json_err

            return {"content": json_content}

        except ValueError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            self._handle_openrouter_error(e, "JSON generation")
            raise  # For type checker (error handler always raises)

    async def generate_ebook_content(self, prompt: str) -> dict[str, str]:
        """Generate ebook content from prompt using OpenRouter"""
        if not self.client:
            raise ValueError(
                "Configuration incomplète: la clé API LLM_API_KEY est manquante. "
                "Veuillez ajouter votre clé API dans le fichier .env"
            )

        try:
            # Generate ebook content using OpenRouter API
            logger.info(f"Generating ebook content using OpenRouter API (model: {self.model})")

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

            # Call OpenRouter API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4000,
                temperature=0.7,
                extra_headers={
                    "HTTP-Referer": "https://ebook-generator.app",
                    "X-Title": "Ebook Generator Backoffice",
                },
            )

            content = response.choices[0].message.content

            # Generate title from the prompt
            title_prompt = (
                f"Génère un titre accrocheur et professionnel pour un ebook sur: {prompt}. "
                "Réponds uniquement avec le titre, sans guillemets."
            )

            title_response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": title_prompt}],
                max_tokens=50,
                temperature=0.5,
                extra_headers={
                    "HTTP-Referer": "https://ebook-generator.app",
                    "X-Title": "Ebook Generator Backoffice",
                },
            )

            title = title_response.choices[0].message.content.strip()

            return {"title": title, "content": content, "author": "Assistant IA"}

        except ValueError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            self._handle_openrouter_error(e, "content generation")
            raise  # For type checker (error handler always raises)
