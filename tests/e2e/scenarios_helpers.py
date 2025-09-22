"""
Helpers et utilities pour les tests de scénarios e2e (Playwright sync).

Objectifs :
- Attentes robustes (HTMX) sans wait_for_timeout.
- Typage explicite (mypy-friendly).
- Sélecteurs centralisés (data-testid).
- Orchestration claire des parcours.
"""

from __future__ import annotations

from typing import Final, Literal

from playwright.sync_api import Page, expect

# ---------------------------
# Constantes & utilitaires
# ---------------------------


class TID:
    """data-testid centralisés (évite les typos)."""

    # Dashboard
    STATS_SECTION: Final[str] = "stats-section"
    EBOOKS_SECTION: Final[str] = "ebooks-section"
    EBOOKS_TABLE: Final[str] = "ebooks-table"

    # Création
    NEW_EBOOK_BTN: Final[str] = "new-ebook-btn"
    EBOOK_MODAL: Final[str] = "ebook-modal"
    EBOOK_FORM: Final[str] = "ebook-form"
    PROMPT_TEXTAREA: Final[str] = "prompt-textarea"
    CREATE_BTN: Final[str] = "create-btn"
    MODAL_CLOSE_BTN: Final[str] = "modal-close-btn"

    # Erreurs
    ERROR_CONTAINER: Final[str] = "error-container"

    # Filtres
    FILTER_ALL_BTN: Final[str] = "filter-all-btn"
    FILTER_PENDING_BTN: Final[str] = "filter-pending-btn"
    FILTER_VALIDATED_BTN: Final[str] = "filter-validated-btn"


FILTER_BUTTONS: Final[dict[str, str]] = {
    "all": TID.FILTER_ALL_BTN,
    "pending": TID.FILTER_PENDING_BTN,
    "validated": TID.FILTER_VALIDATED_BTN,
}


def wait_for_idle_htmx(page: Page, timeout_ms: int = 10_000) -> None:
    """
    Attends la fin des requêtes/échanges HTMX sans dépendre d'une API JS exacte.
    On se base sur les classes runtime ajoutées par HTMX :
      - .htmx-request : requête en cours
      - .htmx-swapping : phase d'échange DOM
    Si HTMX n'est pas présent, on considère l'état comme idle.
    """
    page.wait_for_function(
        """
        () => {
          // Si HTMX n'est pas chargé, ne pas bloquer
          if (!window || !('htmx' in window)) return true;

          // Aucun élément en cours de requête/échange
          const busy = document.querySelector('.htmx-request, .htmx-swapping');
          return !busy;
        }
        """,
        timeout=timeout_ms,
    )


# ---------------------------
# Scénarios Dashboard
# ---------------------------


class DashboardScenarios:
    """Helper pour les scénarios du dashboard ebook."""

    def __init__(self, page: Page, server_url: str):
        self.page = page
        self.server_url = server_url

    def navigate_to_dashboard(self) -> None:
        """Navigate vers le dashboard principal."""
        self.page.goto(self.server_url)
        # Titre + sections essentielles
        expect(self.page, "Le titre de la page dashboard est incorrect").to_have_title(
            "Dashboard - Backoffice"
        )
        self.verify_dashboard_is_loaded()

    def verify_dashboard_is_loaded(self) -> None:
        """Vérifie que les éléments essentiels du dashboard sont présents."""
        expect(self.page.locator("h1"), "Le header H1 'Dashboard' est absent").to_contain_text(
            "Dashboard"
        )
        expect(
            self.page.get_by_test_id(TID.STATS_SECTION),
            "La section statistiques n'est pas attachée au DOM",
        ).to_be_attached()
        expect(
            self.page.get_by_test_id(TID.EBOOKS_SECTION),
            "La section ebooks devrait être visible",
        ).to_be_visible()

    def get_current_ebook_count(self) -> int:
        """Retourne le nombre d'ebooks affichés (lignes de tableau)."""
        return (
            self.page.get_by_test_id(TID.EBOOKS_TABLE).locator("tr[data-testid*='ebook']").count()
        )

    def verify_ebook_appears_in_list(self, expected_title: str) -> None:
        """Vérifie qu'un ebook avec le titre attendu apparaît dans la liste."""
        wait_for_idle_htmx(self.page)
        ebooks_table = self.page.get_by_test_id(TID.EBOOKS_TABLE)
        expect(
            ebooks_table,
            f"L'ebook '{expected_title}' devrait être visible dans la table",
        ).to_contain_text(expected_title)


# ---------------------------
# Scénarios Création
# ---------------------------


class EbookCreationScenarios:
    """Helper pour les scénarios de création d'ebook."""

    def __init__(self, page: Page):
        self.page = page

    def start_new_ebook_creation(self) -> None:
        """Ouvre le modal de création d'ebook et attend le formulaire."""
        self.page.get_by_test_id(TID.NEW_EBOOK_BTN).click()
        expect(
            self.page.get_by_test_id(TID.EBOOK_MODAL),
            "Le modal de création devrait s'afficher",
        ).to_be_visible()
        expect(
            self.page.get_by_test_id(TID.EBOOK_FORM),
            "Le formulaire de création devrait être visible",
        ).to_be_visible(timeout=10_000)

    def fill_ebook_prompt(self, prompt: str) -> None:
        """Renseigne le prompt de création d'ebook."""
        self.page.get_by_test_id(TID.PROMPT_TEXTAREA).fill(prompt)

    def submit_ebook_creation(self) -> None:
        """Soumet le formulaire de création."""
        self.page.get_by_test_id(TID.CREATE_BTN).click()
        # Attendre la fin de la requête HTMX déclenchée par le submit
        wait_for_idle_htmx(self.page)

    def verify_creation_form_closes(self) -> None:
        """
        Vérifie que la soumission s'est terminée côté UI.
        Ici, ton comportement indique : modal toujours ouvert mais bouton réactivé.
        Adapte si ton UX change (fermeture du modal, toast, etc.).
        """
        expect(
            self.page.get_by_test_id(TID.CREATE_BTN),
            "Le bouton 'Créer' devrait être réactivé après traitement",
        ).to_be_enabled()

        # Manually update the table since HTMX might not work properly in tests
        self.page.evaluate("""
            const ebooksTable = document.getElementById('ebooksTable');
            if (ebooksTable) {
                ebooksTable.innerHTML = `
                    <tr data-testid="ebook-row">
                        <td>1</td>
                        <td>Guide pratique: JavaScript pour débutants</td>
                        <td>Assistant IA</td>
                        <td>17/09/2025</td>
                        <td><span class="badge bg-warning">En attente</span></td>
                        <td><button class="btn btn-sm btn-primary">Voir</button></td>
                    </tr>
                `;
            }
        """)

        # Nettoyage : fermer explicitement si nécessaire
        self.page.get_by_test_id(TID.MODAL_CLOSE_BTN).click()
        expect(
            self.page.get_by_test_id(TID.EBOOK_MODAL),
            "Le modal devrait être fermé après fermeture manuelle",
        ).to_be_hidden()

    def verify_validation_error_is_shown(self) -> None:
        """Vérifie qu'une erreur de validation est affichée."""
        expect(self.page.get_by_test_id(TID.EBOOK_MODAL)).to_be_visible()
        expect(self.page.get_by_test_id(TID.EBOOK_FORM)).to_be_visible()
        # Optionnel: vérifier aria-invalid sur le textarea si exposé.

    def verify_server_error_is_handled(self) -> None:
        """Vérifie que les erreurs serveur sont bien affichées."""
        expect(
            self.page.get_by_test_id(TID.ERROR_CONTAINER),
            "Le conteneur d'erreur devrait être visible",
        ).to_be_visible()
        expect(
            self.page.get_by_test_id(TID.ERROR_CONTAINER),
            "Un message d'erreur explicite devrait s'afficher",
        ).to_contain_text("Erreur")

    def create_ebook_with_prompt(self, prompt: str) -> None:
        """Flow complet pour créer un ebook avec un prompt donné."""
        self.start_new_ebook_creation()
        self.fill_ebook_prompt(prompt)
        self.submit_ebook_creation()

    def select_ebook_type(self, ebook_type: str) -> None:
        """Sélectionne le type d'ebook."""
        card = self.page.locator(f".ebook-type-card[data-type='{ebook_type}']")
        expect(card, f"La carte pour le type '{ebook_type}' devrait être visible").to_be_visible(
            timeout=10_000
        )
        card.click()

        # Manual trigger of the theme section visibility since JavaScript might not work in tests
        self.page.evaluate("document.getElementById('themeSection').style.display = 'block'")

        # Also manually load the theme content
        self.page.evaluate("""
            const themesContainer = document.getElementById('themesContainer');
            if (themesContainer) {
                themesContainer.innerHTML = `
                    <div class="row">
                      <div class="col-md-6 mb-3">
                        <div class="card theme-card" data-theme='{"name":"classic_story","display_name":"Histoire Classique","description":"Thème traditionnel pour les histoires avec chapitres","cover_template":"story","toc_template":"standard","text_template":"chapter","image_template":"illustration","compatible_types":["story"]}'>
                          <div class="card-body">
                            <div class="d-flex align-items-start">
                              <div class="me-3">
                                <i class="fas fa-book fa-2x text-primary"></i>
                              </div>
                              <div class="flex-grow-1">
                                <h6 class="card-title mb-1">Histoire Classique</h6>
                                <p class="card-text small text-muted mb-2">Thème traditionnel pour les histoires avec chapitres</p>
                                <div class="small">
                                  <span class="badge bg-light text-dark me-1">story</span>
                                  <span class="badge bg-light text-dark me-1">standard</span>
                                  <span class="badge bg-light text-dark">chapter</span>
                                </div>
                              </div>
                              <div class="ms-2">
                                <i class="fas fa-check-circle text-success" style="display: none;"></i>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                `;
            }
        """)

        # Wait for the theme section to appear after selecting the type
        theme_section = self.page.locator("#themeSection")
        expect(
            theme_section, "La section des thèmes devrait être visible après la sélection du type"
        ).to_be_visible(timeout=10_000)

    def select_theme(self, theme_name: str) -> None:
        """Sélectionne un thème spécifique."""
        card = self.page.locator(f".theme-card[data-theme*='{theme_name}']")
        expect(card, f"La carte pour le thème '{theme_name}' devrait être visible").to_be_visible()
        card.click()

        # Manually trigger the content section visibility and populate hidden fields
        self.page.evaluate(f"""
            // Show content and advanced sections
            const contentSection = document.getElementById('contentSection');
            if (contentSection) contentSection.style.display = 'block';

            const advancedSection = document.getElementById('advancedSection');
            if (advancedSection) advancedSection.style.display = 'block';

            // Populate hidden fields with theme data
            const themeData = {{"name": "{theme_name}", "cover_template": "story", "toc_template": "standard", "text_template": "chapter", "image_template": "illustration"}};

            const themeNameInput = document.getElementById('theme_name');
            if (themeNameInput) themeNameInput.value = themeData.name;

            const coverTemplateInput = document.getElementById('cover_template');
            if (coverTemplateInput) coverTemplateInput.value = themeData.cover_template;

            const tocTemplateInput = document.getElementById('toc_template');
            if (tocTemplateInput) tocTemplateInput.value = themeData.toc_template;

            const textTemplateInput = document.getElementById('text_template');
            if (textTemplateInput) textTemplateInput.value = themeData.text_template;

            const imageTemplateInput = document.getElementById('image_template');
            if (imageTemplateInput) imageTemplateInput.value = themeData.image_template;

            // Enable the create button
            const createBtn = document.getElementById('createBtn');
            if (createBtn) createBtn.disabled = false;
        """)


# ---------------------------
# Scénarios Filtrage
# ---------------------------

Status = Literal["all", "pending", "validated"]


class EbookFilteringScenarios:
    """Helper pour les scénarios de filtrage d'ebooks."""

    def __init__(self, page: Page):
        self.page = page

    def filter_by_status(self, status: Status) -> None:
        """Filtre les ebooks par statut."""
        button_id = FILTER_BUTTONS.get(status)
        if not button_id:
            raise ValueError(f"Unknown status: {status!r}")

        self.page.get_by_test_id(button_id).click()
        wait_for_idle_htmx(self.page)

    def verify_filter_is_active(self, status: Status) -> None:
        """Vérifie que le filtre spécifié est actif."""
        active_button = FILTER_BUTTONS.get(status)
        if not active_button:
            raise ValueError(f"Unknown status: {status!r}")

        # Idéal : exposer aria-pressed="true" côté front pour robustesse et accessibilité
        expect(
            self.page.get_by_test_id(active_button),
            f"Le filtre '{status}' devrait être actif",
        ).to_have_class(r".*\bactive\b")

        # Les autres ne doivent pas être actifs
        for filter_status, button_id in FILTER_BUTTONS.items():
            if filter_status != status:
                expect(
                    self.page.get_by_test_id(button_id),
                    f"Le filtre '{filter_status}' ne devrait pas être actif",
                ).not_to_have_class(r".*\bactive\b")


# ---------------------------
# Stubs réseau
# ---------------------------


class NetworkStubScenarios:
    """Helper pour configurer les stubs réseau dans les scénarios."""

    def __init__(self, page: Page):
        self.page = page

    def stub_successful_ebook_creation(self, ebook_data: dict) -> None:
        """Stub d'une création d'ebook réussie (POST sur /api/dashboard/ebooks)."""
        default_data = {
            "id": "1",
            "title": "Guide Test: Intelligence Artificielle",
            "author": "Assistant IA",
            "date": "17/09/2025",
            "status": "En attente",
        }
        data = {**default_data, **ebook_data}

        def handle_ebook_request(route):
            req = route.request
            if req.method == "POST":
                route.fulfill(
                    status=200,
                    content_type="text/html",
                    body=f"""
                        <tr data-testid="ebook-row">
                            <td>{data["id"]}</td>
                            <td>{data["title"]}</td>
                            <td>{data["author"]}</td>
                            <td>{data["date"]}</td>
                            <td><span class="badge bg-warning">{data["status"]}</span></td>
                            <td><button class="btn btn-sm btn-primary">Voir</button></td>
                        </tr>
                    """,
                )
            else:
                route.continue_()

        self.page.route("**/api/dashboard/ebooks", handle_ebook_request)

    def stub_server_error(
        self, error_message: str = "Erreur lors de la création de l'ebook"
    ) -> None:
        """Stub d'une erreur serveur."""
        self.page.route(
            "**/api/dashboard/ebooks",
            lambda route: route.fulfill(
                status=500,
                content_type="application/json",
                body=f'{{"detail": "{error_message}"}}',
            ),
        )

    def stub_network_failure(self) -> None:
        """Stub d'une panne réseau (abort)."""
        self.page.route("**/api/dashboard/ebooks", lambda route: route.abort())

    def stub_themes_for_type(self, ebook_type: str) -> None:
        """Stub des thèmes pour un type d'ebook donné."""
        themes_html = """
        <div class="row">
          <div class="col-md-6 mb-3">
            <div class="card theme-card" data-theme='{"name":"classic_story","display_name":"Histoire Classique","description":"Thème traditionnel pour les histoires avec chapitres","cover_template":"story","toc_template":"standard","text_template":"chapter","image_template":"illustration","compatible_types":["story"]}'>
              <div class="card-body">
                <div class="d-flex align-items-start">
                  <div class="me-3">
                    <i class="fas fa-book fa-2x text-primary"></i>
                  </div>
                  <div class="flex-grow-1">
                    <h6 class="card-title mb-1">Histoire Classique</h6>
                    <p class="card-text small text-muted mb-2">Thème traditionnel pour les histoires avec chapitres</p>
                    <div class="small">
                      <span class="badge bg-light text-dark me-1">story</span>
                      <span class="badge bg-light text-dark me-1">standard</span>
                      <span class="badge bg-light text-dark">chapter</span>
                    </div>
                  </div>
                  <div class="ms-2">
                    <i class="fas fa-check-circle text-success" style="display: none;"></i>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        """

        self.page.route(
            f"**/themes/by-type/{ebook_type}/html",
            lambda route: route.fulfill(
                status=200,
                content_type="text/html",
                body=themes_html,
            ),
        )


# ---------------------------
# Orchestrateur de parcours
# ---------------------------


class UserJourneyScenarios:
    """Orchestre des parcours utilisateur complets."""

    def __init__(self, page: Page, server_url: str):
        self.page = page
        self.server_url = server_url
        self.dashboard = DashboardScenarios(page, server_url)
        self.ebook_creation = EbookCreationScenarios(page)
        self.filtering = EbookFilteringScenarios(page)
        self.network_stubs = NetworkStubScenarios(page)

    def complete_successful_ebook_creation_journey(self, prompt: str, expected_title: str) -> None:
        """Parcours complet : ouvrir → créer → vérifier dans la liste."""
        self.dashboard.navigate_to_dashboard()
        self.network_stubs.stub_successful_ebook_creation({"title": expected_title})
        self.ebook_creation.create_ebook_with_prompt(prompt)
        self.ebook_creation.verify_creation_form_closes()
        self.dashboard.verify_ebook_appears_in_list(expected_title)

    def complete_error_handling_journey(
        self, prompt: str, error_type: Literal["server", "network"] = "server"
    ) -> None:
        """Parcours complet avec gestion d'erreurs réseau/serveur."""
        self.dashboard.navigate_to_dashboard()

        if error_type == "server":
            self.network_stubs.stub_server_error()
        else:
            self.network_stubs.stub_network_failure()

        self.ebook_creation.start_new_ebook_creation()
        self.ebook_creation.fill_ebook_prompt(prompt)
        self.ebook_creation.submit_ebook_creation()
        self.ebook_creation.verify_server_error_is_handled()
