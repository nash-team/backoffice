import pytest
from playwright.sync_api import Page

from .scenarios_helpers import UserJourneyScenarios


@pytest.mark.scenarios
@pytest.mark.smoke
def test_creator_can_successfully_generate_first_ebook(
    page: Page, server_url: str, test_server, isolated_database
) -> None:
    """
    Smoke: un utilisateur crée son premier ebook, il apparaît dans la liste.
    """
    user = UserJourneyScenarios(page, server_url)

    # Given
    user.dashboard.navigate_to_dashboard()
    user.dashboard.verify_dashboard_is_loaded()

    # When
    prompt = (
        "Génère un ebook 'guide pratique' sur 'JavaScript pour débutants' "
        "en chapitres, avec exemples et exercices."
    )
    expected_title = "Guide pratique: JavaScript pour débutants"

    # Stub côté réseau pour rendre le test instantané et déterministe
    user.network_stubs.stub_successful_ebook_creation({"title": expected_title})
    user.ebook_creation.start_new_ebook_creation()
    user.ebook_creation.fill_ebook_prompt(prompt)
    user.ebook_creation.submit_ebook_creation()

    # Then
    user.ebook_creation.verify_creation_form_closes()
    user.dashboard.verify_ebook_appears_in_list(expected_title)
