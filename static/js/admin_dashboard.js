// Admin Dashboard JavaScript

// Load users data table
function loadUsersTable() {
    fetch('/admin/users/list')
        .then(response => response.json())
        .then(data => {
            const tableBody = document.getElementById('users-table-body');
            tableBody.innerHTML = '';
            
            data.forEach(user => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${user.first_name} ${user.last_name}</td>
                    <td>${user.email}</td>
                    <td>${user.role}</td>
                    <td>
                        ${user.resume_path ? 
                            `<button class="btn btn-sm btn-info" onclick="viewDocument('${user.id}_resume')">
                                <i class="fas fa-file"></i> View
                            </button>` : '-'
                        }
                    </td>
                    <td>
                        ${user.permit_path ? 
                            `<button class="btn btn-sm btn-info" onclick="viewDocument('${user.id}_permit')">
                                <i class="fas fa-file-contract"></i> View
                            </button>` : '-'
                        }
                    </td>
                    <td>
                        <span class="badge rounded-pill bg-${getStatusColor(user.verification_status)}">
                            ${user.verification_status}
                        </span>
                    </td>
                    <td>
                        <div class="btn-group" role="group">
                            <button class="btn btn-sm btn-info" onclick="viewUser('${user.id}')">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="btn btn-sm btn-primary" onclick="editUser('${user.id}')">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="deleteUser('${user.id}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        })
        .catch(error => {
            console.error('Error loading users:', error);
            showToast('Error', 'Failed to load users', 'danger');
        });
}

// Load pending documents
function loadPendingDocuments() {
    fetch('/admin/documents/pending')
        .then(response => response.json())
        .then(data => {
            const tableBody = document.getElementById('pending-docs-table-body');
            tableBody.innerHTML = '';
            
            if (data.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="4" class="text-center">No pending documents</td></tr>';
                return;
            }
            
            data.forEach(doc => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${doc.user_name}</td>
                    <td>${doc.type}</td>
                    <td>${formatDate(doc.submitted_date)}</td>
                    <td>
                        <div class="btn-group" role="group">
                            <button class="btn btn-sm btn-info" onclick="viewDocument('${doc.id}')">
                                <i class="fas fa-eye"></i> View
                            </button>
                            <button class="btn btn-sm btn-success" onclick="approveDocument('${doc.id}')">
                                <i class="fas fa-check"></i> Approve
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="rejectDocument('${doc.id}')">
                                <i class="fas fa-times"></i> Reject
                            </button>
                        </div>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        })
        .catch(error => {
            console.error('Error loading documents:', error);
            showToast('Error', 'Failed to load pending documents', 'danger');
        });
}

// User management functions
function viewUser(userId) {
    fetch(`/admin/users/${userId}`)
        .then(response => response.json())
        .then(user => {
            const modalContent = `
                <div class="modal fade" id="userViewModal" tabindex="-1">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">User Details</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="mb-3">
                                    <strong>Name:</strong> ${user.first_name} ${user.last_name}
                                </div>
                                <div class="mb-3">
                                    <strong>Email:</strong> ${user.email}
                                </div>
                                <div class="mb-3">
                                    <strong>Role:</strong> ${user.role}
                                </div>
                                <div class="mb-3">
                                    <strong>Status:</strong> ${user.verification_status}
                                </div>
                                ${user.resume_path ? 
                                    `<div class="mb-3">
                                        <strong>Resume:</strong>
                                        <button class="btn btn-sm btn-info" onclick="viewDocument('${user.id}_resume')">
                                            View Resume
                                        </button>
                                    </div>` : ''
                                }
                                ${user.permit_path ? 
                                    `<div class="mb-3">
                                        <strong>Business Permit:</strong>
                                        <button class="btn btn-sm btn-info" onclick="viewDocument('${user.id}_permit')">
                                            View Permit
                                        </button>
                                    </div>` : ''
                                }
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Remove existing modal if any
            const existingModal = document.getElementById('userViewModal');
            if (existingModal) {
                existingModal.remove();
            }
            
            // Add new modal
            document.body.insertAdjacentHTML('beforeend', modalContent);
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('userViewModal'));
            modal.show();
        })
        .catch(error => showToast('Error', 'Failed to load user details', 'danger'));
}

function deleteUser(userId) {
    if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
        return;
    }
    
    fetch(`/admin/users/${userId}`, { 
        method: 'DELETE',
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Success', 'User deleted successfully', 'success');
            loadUsersTable();
            updateDashboard();
        } else {
            showToast('Error', data.message, 'danger');
        }
    })
    .catch(error => showToast('Error', 'Failed to delete user', 'danger'));
}

// Document management functions
function viewDocument(docId) {
    window.open(`/admin/documents/${docId}/view`, '_blank');
}

function approveDocument(docId) {
    if (!confirm('Are you sure you want to approve this document?')) {
        return;
    }
    
    fetch(`/admin/documents/${docId}/approve`, { 
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Success', 'Document approved successfully', 'success');
            loadPendingDocuments();
            updateDashboard();
        } else {
            showToast('Error', data.message, 'danger');
        }
    })
    .catch(error => showToast('Error', 'Failed to approve document', 'danger'));
}

function rejectDocument(docId) {
    const reason = prompt('Please enter the reason for rejection:');
    if (!reason) return;
    
    fetch(`/admin/documents/${docId}/reject`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify({ reason: reason })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Success', 'Document rejected successfully', 'success');
            loadPendingDocuments();
            updateDashboard();
        } else {
            showToast('Error', data.message, 'danger');
        }
    })
    .catch(error => showToast('Error', 'Failed to reject document', 'danger'));
}

// Utility functions
function getStatusColor(status) {
    switch (status.toLowerCase()) {
        case 'pending':
            return 'warning';
        case 'verified':
            return 'success';
        case 'rejected':
            return 'danger';
        default:
            return 'secondary';
    }
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleString();
}

function showToast(title, message, type) {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <strong>${title}</strong>: ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    const container = document.getElementById('toast-container');
    container.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

// Document ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Load initial data
    loadUsersTable();
    loadPendingDocuments();
    
    // Set up refresh intervals
    setInterval(loadUsersTable, 30000); // Refresh every 30 seconds
    setInterval(loadPendingDocuments, 30000);
});

// Load users data table
function loadUsersTable() {
    fetch('/admin/users/list')
        .then(response => response.json())
        .then(data => {
            const tableBody = document.getElementById('users-table-body');
            tableBody.innerHTML = '';
            
            data.forEach(user => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${user.first_name} ${user.last_name}</td>
                    <td>${user.email}</td>
                    <td>${user.role}</td>
                    <td>
                        ${user.resume_path ? '<i class="fas fa-file text-success"></i>' : '-'}
                    </td>
                    <td>
                        ${user.permit_path ? '<i class="fas fa-file-contract text-success"></i>' : '-'}
                    </td>
                    <td>${user.verification_status}</td>
                    <td>
                        <button class="btn btn-sm btn-info" onclick="viewUser('${user.id}')">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-primary" onclick="editUser('${user.id}')">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deleteUser('${user.id}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        })
        .catch(error => console.error('Error loading users:', error));
}

// Load pending documents
function loadPendingDocuments() {
    fetch('/admin/documents/pending')
        .then(response => response.json())
        .then(data => {
            const tableBody = document.getElementById('pending-docs-table-body');
            tableBody.innerHTML = '';
            
            data.forEach(doc => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${doc.user_name}</td>
                    <td>${doc.type}</td>
                    <td>${doc.submitted_date}</td>
                    <td>
                        <button class="btn btn-sm btn-info" onclick="viewDocument('${doc.id}')">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-success" onclick="approveDocument('${doc.id}')">
                            <i class="fas fa-check"></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="rejectDocument('${doc.id}')">
                            <i class="fas fa-times"></i>
                        </button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        })
        .catch(error => console.error('Error loading documents:', error));
}

// User management functions
function viewUser(userId) {
    window.location.href = `/admin/users/${userId}`;
}

function editUser(userId) {
    window.location.href = `/admin/users/${userId}/edit`;
}

function deleteUser(userId) {
    if (confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
        fetch(`/admin/users/${userId}`, { method: 'DELETE' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('Success', 'User deleted successfully', 'success');
                    loadUsersTable();
                } else {
                    showToast('Error', data.message, 'error');
                }
            })
            .catch(error => showToast('Error', 'Failed to delete user', 'error'));
    }
}

// Document management functions
function viewDocument(docId) {
    window.open(`/admin/documents/${docId}/view`, '_blank');
}

function approveDocument(docId) {
    fetch(`/admin/documents/${docId}/approve`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Success', 'Document approved', 'success');
                loadPendingDocuments();
            } else {
                showToast('Error', data.message, 'error');
            }
        })
        .catch(error => showToast('Error', 'Failed to approve document', 'error'));
}

function rejectDocument(docId) {
    const reason = prompt('Please enter the reason for rejection:');
    if (reason) {
        fetch(`/admin/documents/${docId}/reject`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ reason: reason })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Success', 'Document rejected', 'success');
                loadPendingDocuments();
            } else {
                showToast('Error', data.message, 'error');
            }
        })
        .catch(error => showToast('Error', 'Failed to reject document', 'error'));
    }
}

// Helper function for showing toasts
function showToast(title, message, type) {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <strong>${title}</strong>: ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    document.getElementById('toast-container').appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadUsersTable();
    loadPendingDocuments();
    
    // Set up refresh intervals
    setInterval(loadUsersTable, 30000); // Refresh every 30 seconds
    setInterval(loadPendingDocuments, 30000);
});