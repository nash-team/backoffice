// Enhanced Ebook Form JavaScript
console.log('Enhanced ebook form script loaded');

document.addEventListener('DOMContentLoaded', function() {
  console.log('DOM loaded, initializing form...');
  initializeEnhancedEbookForm();
});

// Initialize when loaded via HTMX
document.addEventListener('htmx:afterRequest', function(event) {
  if (event.detail.target.id === 'ebookFormErrors' || event.detail.target.closest('#previewModal')) {
    console.log('HTMX content loaded, initializing form...');
    setTimeout(() => initializeEnhancedEbookForm(), 100);
  }
});

function initializeEnhancedEbookForm() {
  const form = document.getElementById('ebookForm');
  if (!form) {
    console.log('Form not found, skipping initialization');
    return;
  }

  console.log('Initializing enhanced ebook form...');

  const createBtn = document.getElementById('createBtn');
  const themeSection = document.getElementById('themeSection');
  const contentSection = document.getElementById('contentSection');
  const advancedSection = document.getElementById('advancedSection');
  const toggleAdvanced = document.getElementById('toggleAdvanced');
  const advancedOptions = document.getElementById('advancedOptions');

  // Gestion de la sélection du type d'ebook - sur les cartes
  document.querySelectorAll('.ebook-type-card').forEach(card => {
    card.addEventListener('click', function() {
      console.log('Carte cliquée:', this.dataset.type);

      const radio = this.querySelector('input[type="radio"]');
      const type = radio.value;

      // Sélectionner le radio button
      radio.checked = true;

      // Appeler la fonction commune
      handleTypeSelection(type, this);
    });
  });

  // Gestion des options avancées
  if (toggleAdvanced) {
    toggleAdvanced.addEventListener('click', function() {
      if (advancedOptions.style.display === 'none') {
        advancedOptions.style.display = 'block';
        this.innerHTML = '<i class="fas fa-chevron-up"></i>';
      } else {
        advancedOptions.style.display = 'none';
        this.innerHTML = '<i class="fas fa-chevron-down"></i>';
      }
    });
  }

  // Validation du formulaire
  if (form) {
    form.addEventListener('input', updateButtonState);
  }

  // Fonction commune pour gérer la sélection
  function handleTypeSelection(type, cardElement) {
    console.log('Type sélectionné:', type);

    // Mettre à jour l'apparence des cartes
    document.querySelectorAll('.ebook-type-card').forEach(c => {
      c.classList.remove('selected');
    });
    cardElement.classList.add('selected');

    // Charger les thèmes compatibles
    loadThemesForType(type);

    // Mettre à jour le placeholder du prompt selon le type
    updatePromptPlaceholder(type);

    // Afficher les sections suivantes
    if (themeSection) {
      themeSection.style.display = 'block';
    }
    updateButtonState();
  }

  function loadThemesForType(type) {
    console.log('Chargement des thèmes pour:', type);

    // Utiliser fetch au lieu de htmx pour plus de contrôle
    fetch(`/themes/by-type/${type}/html`)
      .then(response => response.text())
      .then(html => {
        const themesContainer = document.getElementById('themesContainer');
        if (themesContainer) {
          themesContainer.innerHTML = html;
          console.log('Thèmes chargés avec succès');
          // Après chargement des thèmes, ajouter les event listeners
          setupThemeSelection();
        }
      })
      .catch(error => {
        console.error('Erreur lors du chargement des thèmes:', error);
        const themesContainer = document.getElementById('themesContainer');
        if (themesContainer) {
          themesContainer.innerHTML = '<div class="alert alert-danger">Erreur lors du chargement des thèmes</div>';
        }
      });
  }

  function setupThemeSelection() {
    console.log('Configuration de la sélection de thèmes...');

    document.querySelectorAll('.theme-card').forEach(card => {
      card.addEventListener('click', function() {
        console.log('Thème sélectionné:', this.dataset.theme);

        // Désélectionner les autres thèmes
        document.querySelectorAll('.theme-card').forEach(c => c.classList.remove('selected'));
        this.classList.add('selected');

        // Mettre à jour les champs cachés
        try {
          const themeData = JSON.parse(this.dataset.theme);

          const themeNameInput = document.getElementById('theme_name');
          const coverTemplateInput = document.getElementById('cover_template');
          const tocTemplateInput = document.getElementById('toc_template');
          const textTemplateInput = document.getElementById('text_template');
          const imageTemplateInput = document.getElementById('image_template');

          if (themeNameInput) themeNameInput.value = themeData.name;
          if (coverTemplateInput) coverTemplateInput.value = themeData.cover_template;
          if (tocTemplateInput) tocTemplateInput.value = themeData.toc_template;
          if (textTemplateInput) textTemplateInput.value = themeData.text_template;
          if (imageTemplateInput) imageTemplateInput.value = themeData.image_template;

          // Afficher les sections suivantes
          if (contentSection) {
            contentSection.style.display = 'block';
          }
          if (advancedSection) {
            advancedSection.style.display = 'block';
          }
          updateButtonState();
        } catch (e) {
          console.error('Erreur lors du parsing des données du thème:', e);
        }
      });
    });
  }

  function updatePromptPlaceholder(type) {
    const promptTextarea = document.getElementById('prompt');
    if (!promptTextarea) return;

    const placeholders = {
      'story': 'Ex: Génère une histoire pour enfants sur une petite fille qui découvre un jardin magique peuplé de créatures fantastiques. L\'histoire doit comporter 3 chapitres courts et être adaptée aux enfants de 6-10 ans.',
      'coloring': 'Ex: Génère un livre de coloriage sur le thème des animaux de la forêt. Créer 8 pages avec des illustrations simples et amusantes : un écureuil, un lapin, un hibou, etc. Chaque image doit être adaptée au coloriage par des enfants de 4-8 ans.',
      'mixed': 'Ex: Génère une aventure interactive combinant histoire et coloriage sur le thème des pirates. 2 chapitres d\'histoire alternés avec 2 pages de coloriage (bateau pirate, trésor). Pour enfants de 5-9 ans.'
    };

    if (placeholders[type]) {
      promptTextarea.placeholder = placeholders[type];
    }
  }

  function updateButtonState() {
    if (!createBtn) return;

    const typeSelected = document.querySelector('input[name="ebook_type"]:checked');
    const themeSelected = document.querySelector('.theme-card.selected');
    const promptElement = document.getElementById('prompt');
    const promptFilled = promptElement ? promptElement.value.trim() : false;

    // Le titre n'est plus obligatoire (peut être généré automatiquement)
    const canCreate = typeSelected && themeSelected && promptFilled;
    createBtn.disabled = !canCreate;

    console.log('Validation:', {
      typeSelected: !!typeSelected,
      themeSelected: !!themeSelected,
      promptFilled: !!promptFilled,
      canCreate
    });
  }

  console.log('Enhanced ebook form initialized successfully');
}