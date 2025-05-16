// Vérifier si l'utilisateur est connecté
function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
    }
    return token;
}

// Fonction de déconnexion
function logout() {
    localStorage.removeItem('token');
    window.location.href = '/login';
}

// Charger les données du tableau de bord
async function loadDashboardData() {
    const token = checkAuth();
    
    try {
        // Charger les statistiques
        const statsResponse = await fetch('/api/dashboard/stats', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        const stats = await statsResponse.json();
        
        document.getElementById('totalEbooks').textContent = stats.total_ebooks;
        document.getElementById('pendingEbooks').textContent = stats.pending_ebooks;
        document.getElementById('validatedEbooks').textContent = stats.validated_ebooks;

        // Charger la liste des ebooks depuis la BDD
        const ebooksResponse = await fetch('/api/ebooks', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        const ebooks = await ebooksResponse.json();
        
        const tableBody = document.getElementById('ebooksTable');
        tableBody.innerHTML = ebooks.map(ebook => `
            <tr>
                <td>${ebook.id}</td>
                <td>${ebook.title}</td>
                <td>${ebook.author}</td>
                <td>${new Date(ebook.created_at).toLocaleDateString()}</td>
                <td>
                    <span class="badge ${ebook.status === 'pending' ? 'bg-warning' : 'bg-success'}">
                        ${ebook.status === 'pending' ? 'En attente' : 'Validé'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-primary btn-action" onclick="viewEbook('${ebook.drive_id}')">Voir</button>
                    <button class="btn btn-sm btn-warning btn-action" onclick="editEbook('${ebook.id}')">Modifier</button>
                    <button class="btn btn-sm btn-danger btn-action" onclick="deleteEbook('${ebook.id}')">Supprimer</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Erreur lors du chargement des données:', error);
        if (error.status === 401) {
            logout();
        }
    }
}

// Fonctions pour les actions sur les ebooks
async function viewEbook(driveId) {
    const token = checkAuth();
    try {
        // Récupérer l'URL de prévisualisation depuis Google Drive
        const response = await fetch(`/api/drive/ebooks/${driveId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        const ebook = await response.json();
        
        if (ebook.preview_url) {
            window.open(ebook.preview_url, '_blank');
        } else {
            alert('URL de prévisualisation non disponible');
        }
    } catch (error) {
        console.error('Erreur lors de la récupération de l\'ebook:', error);
        alert('Erreur lors de l\'accès au fichier');
    }
}

function editEbook(id) {
    // TODO: Implémenter l'édition
    console.log('Modifier ebook:', id);
}

function deleteEbook(id) {
    if (confirm('Êtes-vous sûr de vouloir supprimer cet ebook ?')) {
        // TODO: Implémenter la suppression
        console.log('Supprimer ebook:', id);
    }
}

// Fonction pour filtrer les ebooks
async function filterEbooks(status) {
    const token = checkAuth();
    try {
        const response = await fetch(`/api/ebooks${status ? `?status=${status}` : ''}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        const ebooks = await response.json();
        
        const tableBody = document.getElementById('ebooksTable');
        tableBody.innerHTML = ebooks.map(ebook => `
            <tr>
                <td>${ebook.id}</td>
                <td>${ebook.title}</td>
                <td>${ebook.author}</td>
                <td>${new Date(ebook.created_at).toLocaleDateString()}</td>
                <td>
                    <span class="badge ${ebook.status === 'pending' ? 'bg-warning' : 'bg-success'}">
                        ${ebook.status === 'pending' ? 'En attente' : 'Validé'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-primary btn-action" onclick="viewEbook('${ebook.drive_id}')">Voir</button>
                    <button class="btn btn-sm btn-warning btn-action" onclick="editEbook('${ebook.id}')">Modifier</button>
                    <button class="btn btn-sm btn-danger btn-action" onclick="deleteEbook('${ebook.id}')">Supprimer</button>
                </td>
            </tr>
        `).join('');

        // Mettre à jour l'état actif des boutons de filtre
        document.querySelectorAll('.btn-group .btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.textContent.toLowerCase().includes(status || 'all')) {
                btn.classList.add('active');
            }
        });
    } catch (error) {
        console.error('Erreur lors du filtrage des ebooks:', error);
    }
}

// Charger les données au chargement de la page
document.addEventListener('DOMContentLoaded', loadDashboardData); 