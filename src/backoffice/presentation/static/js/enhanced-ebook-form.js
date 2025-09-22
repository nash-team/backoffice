// Enhanced Ebook Form JavaScript - Ultra simplifié avec hyperscript
console.log('Enhanced ebook form script loaded');

// ============================================================================
// FONCTIONS UTILITAIRES POUR HYPERSCRIPT
// ============================================================================

// Fonction pour mettre à jour les placeholders
window.updatePromptPlaceholder = function(type) {
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
};

// Fonction pour configurer un thème depuis une carte
window.setupThemeFromCard = function(card) {
  try {
    const themeData = JSON.parse(card.dataset.theme);

    // Mettre à jour les champs cachés
    ['theme_name', 'cover_template', 'toc_template', 'text_template', 'image_template'].forEach(field => {
      const input = document.getElementById(field);
      if (input && themeData[field.replace('_template', '_template')]) {
        input.value = themeData[field.replace('_template', '_template')] || themeData.name;
      }
    });

    // Afficher les sections suivantes
    ['contentSection', 'advancedSection'].forEach(section => {
      const el = document.getElementById(section);
      if (el) el.style.display = 'block';
    });
  } catch (e) {
    console.error('Erreur parsing thème:', e);
  }
};

// Fonction d'initialisation minimale
window.initializeEnhancedEbookForm = function() {
  console.log('Form initialized with hyperscript');
  // La plupart de la logique est maintenant dans hyperscript !
};