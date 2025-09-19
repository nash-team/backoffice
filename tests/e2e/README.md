# Tests E2E Orientés Scénarios

Cette nouvelle structure de tests E2E est conçue pour tester des **scénarios utilisateur complets** plutôt que des fonctionnalités techniques isolées.

## 🎯 Philosophie des Tests de Scénarios

### Nouvelle Approche (Orientée Scénarios)

- Tests narratifs : `test_creator_can_successfully_generate_their_first_ebook()`
- Focus utilisateur : "Est-ce que Marie peut accomplir sa tâche ?"
- Parcours complets du début à la fin
- Structure Given-When-Then pour clarté

## 📁 Structure des Fichiers

### `scenarios_helpers.py`

Helpers réutilisables pour construire des scénarios :

- `DashboardScenarios` : Actions sur le dashboard
- `EbookCreationScenarios` : Flux de création d'ebooks  
- `EbookFilteringScenarios` : Filtrage et organisation
- `NetworkStubScenarios` : Simulation d'erreurs réseau
- `UserJourneyScenarios` : Orchestration de parcours complets

### `test_user_scenarios_e2e.py`

**Scénarios utilisateur principaux** avec des personas :

- `TestContentCreatorJourneys` : Marie, créatrice de contenu
- `TestContentManagerJourneys` : Jean, gestionnaire éditorial
- `TestResilientUserExperience` : Gestion d'erreurs gracieuse
- `TestCompleteWorkflows` : Workflows de bout en bout

### `test_advanced_scenarios_e2e.py`

**Scénarios avancés et edge cases** :

- `TestEdgeCasesAndCornerSituations` : Cas limites
- `TestRecoveryAndResilienceScenarios` : Récupération d'erreurs
- `TestAdvancedWorkflowScenarios` : Workflows complexes
- `TestCrossFeatureIntegrationScenarios` : Intégration entre features

### `test_technical_quality_e2e.py`

**Tests de qualité technique** (séparés des scénarios métier) :

- `TestAccessibilityCompliance` : WCAG, navigation clavier
- `TestResponsiveDesign` : Mobile, tablette, desktop
- `TestPerformanceQuality` : Temps de chargement
- `TestCrossBrowserQuality` : Compatibilité navigateurs

## 🏃‍♂️ Exécution des Tests

### Tests par Catégorie

```bash
# Tous les scénarios utilisateur
pytest -m scenarios

# Tests de fumée rapides  
pytest -m "scenarios and smoke"

# Tests d'intégration complets
pytest -m "scenarios and integration"

# Edge cases et récupération
pytest -m "edge_cases or recovery"

# Qualité technique uniquement
pytest -m "accessibility or responsive or performance"
```

### Tests par Niveau de Complexité

```bash
# Scénarios de base (smoke)
pytest tests/e2e/test_user_scenarios_e2e.py::TestContentCreatorJourneys

# Scénarios avancés
pytest tests/e2e/test_advanced_scenarios_e2e.py

# Qualité technique
pytest tests/e2e/test_technical_quality_e2e.py
```

## 📖 Écriture de Nouveaux Scénarios

### Template de Scénario Utilisateur

```python
async def test_user_accomplishes_meaningful_task(
    self, page: Page, server_url: str, test_server, isolated_database
):
    """
    Scénario: Description claire de ce que l'utilisateur veut faire
    
    GIVEN contexte de départ de l'utilisateur
    WHEN actions que l'utilisateur effectue  
    THEN résultat attendu du point de vue utilisateur
    """
    user_journey = UserJourneyScenarios(page, server_url)
    
    # Given: État initial clair
    # When: Actions utilisateur réalistes
    # Then: Vérifications orientées valeur métier
```

### Règles pour les Scénarios

1. **Nommage** : `test_[persona]_[can|accomplishes]_[meaningful_task]()`
2. **Structure** : Toujours Given-When-Then explicite
3. **Persona** : Utiliser des personas réalistes (Marie la créatrice, Jean le manager)
4. **Parcours Complet** : Du début à la fin, pas de fragments
5. **Valeur Métier** : Se concentrer sur la valeur pour l'utilisateur

### Helpers vs Tests Directs

**Utiliser les helpers** pour les actions communes :

```python
# ✅ Bon
await user_journey.complete_successful_ebook_creation_journey(prompt, title)

# ❌ Éviter la répétition
user_journey.dashboard.navigate_to_dashboard()
user_journey.ebook_creation.start_new_ebook_creation()
# ... 10 lignes répétées dans chaque test
```

**Tests directs** pour les cas spécifiques uniques :

```python
# ✅ Bon pour tester un comportement spécifique
page.get_by_test_id("prompt-textarea").fill(very_long_prompt)
textarea = page.get_by_test_id("prompt-textarea")
filled_content = await textarea.input_value()
assert len(filled_content) > 1500
```

## 🎭 Personas et Contextes

### Marie - Créatrice de Contenu Tech

- Veut créer des guides rapidement
- Valorise l'efficacité et la simplicité
- Scénarios : premier ebook, création en série, gestion d'erreurs

### Jean - Gestionnaire Éditorial  

- Supervise et organise les contenus
- A besoin de vues d'ensemble et de filtrage
- Scénarios : organisation par statut, priorisation, workflows collaboratifs

### Utilisateurs en Situation d'Erreur

- Problèmes réseau, sessions expirées
- Scénarios de récupération et résilience
- Focus sur la graceful degradation

## 🔧 Maintenance et Évolution

### Ajout d'une Nouvelle Fonctionnalité

1. **Créer les helpers** dans `scenarios_helpers.py`
2. **Écrire les scénarios** principaux dans `test_user_scenarios_e2e.py`
3. **Ajouter les edge cases** dans `test_advanced_scenarios_e2e.py`
4. **Tests techniques** (si applicable) dans `test_technical_quality_e2e.py`

### Refactoring de Tests Existants

1. Identifier le **vrai scénario utilisateur** derrière le test technique
2. Créer une **histoire avec persona** et contexte métier
3. Restructurer en **Given-When-Then** explicite
4. Utiliser les **helpers appropriés** pour éviter la duplication

## 📈 Avantages de cette Approche

✅ **Lisibilité** : Les tests racontent une histoire métier claire  
✅ **Maintenance** : Helpers réutilisables, moins de duplication  
✅ **Couverture** : Parcours utilisateur complets vs fragments  
✅ **Debug** : Plus facile de comprendre les échecs en contexte  
✅ **Documentation** : Les tests documentent les cas d'usage réels  
✅ **Séparation** : Scénarios métier vs tests techniques séparés
