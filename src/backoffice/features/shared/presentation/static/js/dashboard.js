// Dashboard JavaScript - Intégrations Bootstrap uniquement
// Logique HTMX gérée par attributs HTML

// === Logout avec redirection (localStorage + navigation) ===
document.body.addEventListener('htmx:afterRequest', (e) => {
    if (e.target.id === 'logoutBtn' && e.detail.xhr.status < 400) {
        localStorage.removeItem('token');
        window.location.href = '/login';
    }
});

// === Gestion filtres actifs (états visuels complexes) ===
document.body.addEventListener('htmx:beforeRequest', (e) => {
    if (e.target.classList.contains('filter-btn')) {
        // Remove active class from all filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        // Add active class to current button
        e.target.classList.add('active');
    }
});

// === Toasts d'erreur Bootstrap (API Bootstrap) ===
function createToast(message, type = 'danger') {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0 position-fixed top-0 end-0 m-3`;
    toast.style.zIndex = '9999';
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Fermer"></button>
        </div>
    `;

    document.body.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    // Remove toast after hiding
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

// === Error Handling avec Bootstrap Toasts ===
document.body.addEventListener('htmx:responseError', (e) => {
    console.error('HTMX Error:', e.detail);

    // Try to extract error message from response HTML
    let errorMessage = 'Erreur lors de la requête. Veuillez réessayer.';

    try {
        const responseText = e.detail.xhr.responseText;
        if (responseText) {
            // Parse the HTML response to extract error message
            const parser = new DOMParser();
            const doc = parser.parseFromString(responseText, 'text/html');
            const alertDiv = doc.querySelector('.alert-danger');

            if (alertDiv) {
                // Extract text content, removing the icon
                const icon = alertDiv.querySelector('i');
                if (icon) icon.remove();
                errorMessage = alertDiv.textContent.trim();
            }
        }
    } catch (err) {
        console.error('Error parsing response:', err);
    }

    createToast(errorMessage);
});

// === Network Error Handling ===
document.body.addEventListener('htmx:sendError', (e) => {
    console.error('HTMX Network Error:', e.detail);
    createToast('Problème de connexion. Vérifiez votre réseau.', 'warning');
});

// === Ebook Creation Success - Close Modal ===
document.body.addEventListener('ebook:created', (e) => {
    console.log('Ebook créé avec succès, fermeture de la modal...');

    // Fermer la modal
    const modal = document.getElementById('previewModal');
    if (modal) {
        const modalInstance = bootstrap.Modal.getInstance(modal);
        if (modalInstance) {
            modalInstance.hide();
        } else {
            // Fallback: create instance and hide
            const newModalInstance = new bootstrap.Modal(modal);
            newModalInstance.hide();
        }
    }

    // Afficher un toast de succès
    createToast('Ebook créé avec succès !', 'success');
});

// === Modal Keyboard Support (Bootstrap API) ===
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const modal = document.getElementById('previewModal');
        if (modal && modal.classList.contains('show')) {
            const modalInstance = bootstrap.Modal.getInstance(modal);
            if (modalInstance) {
                modalInstance.hide();
            } else {
                // Fallback: create instance and hide
                const newModalInstance = new bootstrap.Modal(modal);
                newModalInstance.hide();
            }
        }
    }
});

// ========================================
// KDP Preview Functions (shared across templates)
// ========================================

/**
 * Show full PDF preview - reloads page to restore original PDF viewer
 * @param {HTMLElement} button - Button element (unused, kept for backward compatibility)
 */
window.showFullPDFPreview = function(button) {
    location.reload();
};

/**
 * Show KDP Cover preview (back + spine + front with overlay)
 * @param {number} ebookId - Ebook ID
 */
window.showKDPCoverPreview = function(ebookId) {
    const pdfContainer = document.querySelector('.pdf-viewer-container');
    if (!pdfContainer) {
        console.error('PDF container not found');
        return;
    }

    // Show loading state
    pdfContainer.innerHTML = `
        <div class="d-flex flex-column align-items-center justify-content-center h-100" style="min-height: 600px;">
            <div class="spinner-border text-primary mb-3" role="status">
                <span class="visually-hidden">Génération de l'aperçu cover KDP...</span>
            </div>
            <p class="text-muted">Génération de l'aperçu cover KDP en cours...</p>
            <small class="text-muted">Assemblage: back + spine + front avec overlay KDP...</small>
        </div>
    `;

    // Load KDP cover preview image
    setTimeout(() => {
        pdfContainer.innerHTML = `
            <div class="text-center p-4" style="background: #f8f9fa; border-radius: 0.375rem; overflow: auto;">
                <img
                    src="/api/ebooks/${ebookId}/kdp-cover-preview"
                    alt="KDP Cover Preview"
                    style="max-width: 100%; height: auto; border: 1px solid #dee2e6; border-radius: 0.375rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"
                    data-testid="kdp-cover-preview-img">
                <p class="text-muted mt-3 small">
                    <i class="fas fa-info-circle me-1"></i>
                    Vérifiez que le contenu important est bien dans les zones de sécurité (évitez les zones rouges du template)
                </p>
            </div>
        `;
    }, 100);
};

/**
 * Show KDP Interior preview (interior pages only, no cover)
 * @param {number} ebookId - Ebook ID
 */
window.showKDPInteriorPreview = function(ebookId) {
    const pdfContainer = document.querySelector('.pdf-viewer-container');
    if (!pdfContainer) {
        console.error('PDF container not found');
        return;
    }

    // Show loading state
    pdfContainer.innerHTML = `
        <div class="d-flex flex-column align-items-center justify-content-center h-100" style="min-height: 600px;">
            <div class="spinner-border text-primary mb-3" role="status">
                <span class="visually-hidden">Génération de l'aperçu Interior KDP...</span>
            </div>
            <p class="text-muted">Génération de l'aperçu Interior KDP en cours...</p>
            <small class="text-muted">Pages intérieures uniquement (sans cover ni back cover)</small>
        </div>
    `;

    // Load KDP Interior PDF preview
    setTimeout(() => {
        pdfContainer.innerHTML = `
            <iframe
                src="/api/ebooks/${ebookId}/export-kdp/interior?preview=true"
                width="100%"
                height="600"
                frameborder="0"
                style="border-radius: 0.375rem;"
                data-testid="kdp-interior-preview">
            </iframe>
        `;
    }, 100);
};

// ========================================
// Multi-Page Regeneration Functions
// ========================================

/**
 * Select all pages in the regeneration modal
 * @param {number} ebookId - Ebook ID
 */
window.selectAllPages = function(ebookId) {
    document.querySelectorAll(`.page-checkbox-${ebookId}`).forEach(checkbox => {
        checkbox.checked = true;
    });
};

/**
 * Deselect all pages in the regeneration modal
 * @param {number} ebookId - Ebook ID
 */
window.deselectAllPages = function(ebookId) {
    document.querySelectorAll(`.page-checkbox-${ebookId}`).forEach(checkbox => {
        checkbox.checked = false;
    });
};

/**
 * Regenerate selected pages via API
 * @param {number} ebookId - Ebook ID
 */
window.regenerateSelectedPages = async function(ebookId) {
    // Get all checked pages
    const selectedPages = Array.from(document.querySelectorAll(`.page-checkbox-${ebookId}:checked`))
        .map(checkbox => parseInt(checkbox.value, 10));

    if (selectedPages.length === 0) {
        createToast('Veuillez sélectionner au moins une page', 'warning');
        return;
    }

    // Show loading state
    const spinner = document.getElementById(`regenerateSelectedSpinner-${ebookId}`);
    const btn = document.getElementById(`regenerateSelectedBtn-${ebookId}`);

    if (spinner) spinner.classList.remove('d-none');
    if (btn) btn.disabled = true;

    try {
        const response = await fetch(`/api/ebooks/${ebookId}/pages/regenerate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                page_type: 'content_page',
                page_indices: selectedPages
            })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            createToast(result.message || `${selectedPages.length} page(s) régénérée(s) avec succès !`, 'success');

            // Close the multi-page modal
            const modal = bootstrap.Modal.getInstance(document.getElementById(`multiPageRegenerateModal-${ebookId}`));
            if (modal) modal.hide();

            // Reload after 2 seconds to show updated PDF
            setTimeout(() => { location.reload(); }, 2000);
        } else {
            createToast(result.detail || 'Erreur lors de la régénération', 'danger');
        }
    } catch (error) {
        console.error('Error regenerating pages:', error);
        createToast('Erreur lors de la régénération des pages', 'danger');
    } finally {
        if (spinner) spinner.classList.add('d-none');
        if (btn) btn.disabled = false;
    }
};