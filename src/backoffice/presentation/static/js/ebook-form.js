// Ebook Form JavaScript - Intégration Bootstrap uniquement
// États boutons/spinners gérés par HTMX automatiquement

// === Modal Bootstrap integration (pas possible en HTMX pur) ===
document.body.addEventListener('ebook:created', () => {
    const modalEl = document.getElementById('previewModal');
    bootstrap.Modal.getOrCreateInstance(modalEl).hide();

    // Rafraîchir les stats via HTMX
    htmx.ajax('GET', '/api/dashboard/stats', {
        target: '.row.mb-4',
        swap: 'innerHTML'
    });
});