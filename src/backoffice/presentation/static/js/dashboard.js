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
    createToast('Erreur lors de la requête. Veuillez réessayer.');
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