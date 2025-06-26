// GeRot - Sistema de Gerenciamento de Rotinas
// JavaScript Principal

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    setupSidebar();
    setupModals();
    setupForms();
    setupTasks();
    setupAlerts();
    setupCalendar();
}

// ==================== SIDEBAR ====================
function setupSidebar() {
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main-content');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            sidebar.classList.toggle('active');
            
            // Fechar sidebar ao clicar fora (mobile)
            if (window.innerWidth <= 768) {
                setTimeout(() => {
                    document.addEventListener('click', closeSidebarOnOutsideClick);
                }, 100);
            }
        });
    }
    
    function closeSidebarOnOutsideClick(e) {
        if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
            sidebar.classList.remove('active');
            document.removeEventListener('click', closeSidebarOnOutsideClick);
        }
    }
}

// ==================== MODAIS ====================
function setupModals() {
    // Abrir modais
    document.querySelectorAll('[data-modal-target]').forEach(trigger => {
        trigger.addEventListener('click', function(e) {
            e.preventDefault();
            const modalId = this.getAttribute('data-modal-target');
            openModal(modalId);
        });
    });
    
    // Fechar modais
    document.querySelectorAll('.modal-close, [data-modal-close]').forEach(closeBtn => {
        closeBtn.addEventListener('click', function() {
            const modal = this.closest('.modal');
            if (modal) closeModal(modal.id);
        });
    });
    
    // Fechar modal ao clicar no overlay
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeModal(this.id);
            }
        });
    });
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
        
        // Focus no primeiro input
        const firstInput = modal.querySelector('input, textarea, select');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// ==================== FORMULÁRIOS ====================
function setupForms() {
    // Submit com loading
    document.querySelectorAll('form[data-loading]').forEach(form => {
        form.addEventListener('submit', function() {
            showLoading();
        });
    });
    
    // Validação em tempo real
    document.querySelectorAll('.form-control[required]').forEach(input => {
        input.addEventListener('blur', validateField);
        input.addEventListener('input', clearFieldError);
    });
    
    // Adicionar tarefas dinâmicamente
    const addTaskBtn = document.getElementById('add-task-btn');
    if (addTaskBtn) {
        addTaskBtn.addEventListener('click', addTaskField);
    }
}

function validateField(e) {
    const field = e.target;
    const value = field.value.trim();
    
    clearFieldError(e);
    
    if (!value && field.required) {
        showFieldError(field, 'Este campo é obrigatório');
    } else if (field.type === 'email' && value && !isValidEmail(value)) {
        showFieldError(field, 'Email inválido');
    } else if (field.type === 'password' && value && value.length < 6) {
        showFieldError(field, 'Senha deve ter pelo menos 6 caracteres');
    }
}

function clearFieldError(e) {
    const field = e.target;
    const errorDiv = field.parentNode.querySelector('.field-error');
    if (errorDiv) errorDiv.remove();
    field.style.borderColor = '';
}

function showFieldError(field, message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'field-error text-sm text-red-500 mt-1';
    errorDiv.textContent = message;
    field.parentNode.appendChild(errorDiv);
    field.style.borderColor = 'var(--error-color)';
}

function addTaskField() {
    const container = document.getElementById('tasks-container');
    if (!container) return;
    
    const taskCount = container.children.length;
    const taskDiv = document.createElement('div');
    taskDiv.className = 'form-group task-field';
    taskDiv.innerHTML = `
        <div class="flex gap-2">
            <input 
                type="text" 
                name="tasks" 
                class="form-control" 
                placeholder="Digite a tarefa ${taskCount + 1}"
                required
            >
            <select name="priorities" class="form-select" style="width: 120px;">
                <option value="1">Baixa</option>
                <option value="2" selected>Média</option>
                <option value="3">Alta</option>
            </select>
            <input 
                type="number" 
                name="estimated_times" 
                class="form-control" 
                placeholder="Min" 
                min="1" 
                style="width: 80px;"
            >
            <button type="button" class="btn btn-danger btn-sm" onclick="removeTaskField(this)">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `;
    
    container.appendChild(taskDiv);
    taskDiv.querySelector('input').focus();
}

function removeTaskField(btn) {
    btn.closest('.task-field').remove();
}

// ==================== TAREFAS ====================
function setupTasks() {
    // Checkboxes de tarefas
    document.querySelectorAll('.task-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            toggleTask(this);
        });
    });
    
    // Filtros de tarefas
    const filterBtns = document.querySelectorAll('[data-filter]');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const filter = this.getAttribute('data-filter');
            filterTasks(filter);
            
            // Atualizar botões ativos
            filterBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

function toggleTask(checkbox) {
    const taskItem = checkbox.closest('.checklist-item');
    const taskId = checkbox.value;
    
    if (checkbox.checked) {
        taskItem.classList.add('completed');
        completeTask(taskId);
    } else {
        taskItem.classList.remove('completed');
        uncompleteTask(taskId);
    }
    
    updateProgress();
}

function completeTask(taskId) {
    fetch('/api/tasks/complete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ task_id: taskId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Tarefa completada!', 'success');
        }
    })
    .catch(error => {
        console.error('Erro ao completar tarefa:', error);
        showNotification('Erro ao completar tarefa', 'error');
    });
}

function filterTasks(filter) {
    const tasks = document.querySelectorAll('.checklist-item');
    
    tasks.forEach(task => {
        const isCompleted = task.classList.contains('completed');
        const priority = task.querySelector('.priority-badge')?.textContent.toLowerCase();
        
        let show = true;
        
        switch (filter) {
            case 'pending':
                show = !isCompleted;
                break;
            case 'completed':
                show = isCompleted;
                break;
            case 'high':
                show = priority === 'alta';
                break;
            case 'medium':
                show = priority === 'média';
                break;
            case 'low':
                show = priority === 'baixa';
                break;
            default:
                show = true;
        }
        
        task.style.display = show ? 'flex' : 'none';
    });
}

function updateProgress() {
    const totalTasks = document.querySelectorAll('.task-checkbox').length;
    const completedTasks = document.querySelectorAll('.task-checkbox:checked').length;
    const progress = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0;
    
    const progressBar = document.querySelector('.progress-bar');
    const progressText = document.querySelector('.progress-text');
    
    if (progressBar) {
        progressBar.style.width = progress + '%';
    }
    
    if (progressText) {
        progressText.textContent = `${completedTasks}/${totalTasks} tarefas completadas`;
    }
}

// ==================== ALERTAS ====================
function setupAlerts() {
    // Auto-hide alerts
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 300);
            }
        }, 5000);
    });
}

function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} fade-in`;
    alertDiv.innerHTML = `
        <i class="fas fa-${getIconForType(type)}"></i>
        ${message}
        <button type="button" class="alert-close" onclick="this.parentElement.remove()">&times;</button>
    `;
    
    const container = document.querySelector('.alerts-container') || 
                     document.querySelector('.main-content');
    
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        setTimeout(() => {
            alertDiv.style.opacity = '0';
            setTimeout(() => alertDiv.remove(), 300);
        }, 4000);
    }
}

function getIconForType(type) {
    const icons = {
        success: 'check-circle',
        error: 'exclamation-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    };
    return icons[type] || 'info-circle';
}

// ==================== CALENDÁRIO ====================
function setupCalendar() {
    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) return;
    
    // Implementação básica de calendário
    generateCalendar();
}

function generateCalendar() {
    const now = new Date();
    const currentMonth = now.getMonth();
    const currentYear = now.getFullYear();
    const today = now.getDate();
    
    const monthNames = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ];
    
    const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
    const firstDayOfMonth = new Date(currentYear, currentMonth, 1).getDay();
    
    const calendarHeader = document.getElementById('calendar-header');
    const calendarBody = document.getElementById('calendar-body');
    
    if (calendarHeader) {
        calendarHeader.textContent = `${monthNames[currentMonth]} ${currentYear}`;
    }
    
    if (calendarBody) {
        let html = '';
        
        // Dias da semana
        const dayNames = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
        html += '<div class="calendar-week calendar-header">';
        dayNames.forEach(day => {
            html += `<div class="calendar-day-header">${day}</div>`;
        });
        html += '</div>';
        
        // Dias do mês
        let dayCount = 1;
        for (let week = 0; week < 6; week++) {
            html += '<div class="calendar-week">';
            
            for (let day = 0; day < 7; day++) {
                if (week === 0 && day < firstDayOfMonth) {
                    html += '<div class="calendar-day empty"></div>';
                } else if (dayCount <= daysInMonth) {
                    const isToday = dayCount === today;
                    const classes = `calendar-day ${isToday ? 'today' : ''}`;
                    html += `<div class="${classes}" data-date="${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(dayCount).padStart(2, '0')}">
                        <span class="day-number">${dayCount}</span>
                        <div class="day-tasks"></div>
                    </div>`;
                    dayCount++;
                } else {
                    html += '<div class="calendar-day empty"></div>';
                }
            }
            
            html += '</div>';
            
            if (dayCount > daysInMonth) break;
        }
        
        calendarBody.innerHTML = html;
        
        // Adicionar event listeners aos dias
        document.querySelectorAll('.calendar-day:not(.empty)').forEach(day => {
            day.addEventListener('click', function() {
                const date = this.getAttribute('data-date');
                if (date) {
                    showDayTasks(date);
                }
            });
        });
    }
}

function showDayTasks(date) {
    console.log('Mostrando tarefas para:', date);
    // Implementar modal ou sidebar com tarefas do dia
}

// ==================== UTILITÁRIOS ====================
function showLoading() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.classList.add('active');
    }
}

function hideLoading() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.classList.remove('active');
    }
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function formatDate(date) {
    return new Date(date).toLocaleDateString('pt-BR');
}

function formatTime(time) {
    return new Date('2000-01-01 ' + time).toLocaleTimeString('pt-BR', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ==================== API HELPERS ====================
function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    return fetch(url, { ...defaultOptions, ...options })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        });
}

// ==================== EVENTOS GLOBAIS ====================
window.addEventListener('beforeunload', function() {
    hideLoading();
});

// Atalhos de teclado
document.addEventListener('keydown', function(e) {
    // ESC para fechar modais
    if (e.key === 'Escape') {
        const activeModal = document.querySelector('.modal.active');
        if (activeModal) {
            closeModal(activeModal.id);
        }
    }
    
    // Ctrl+S para salvar (prevenir comportamento padrão)
    if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        const saveBtn = document.querySelector('.btn-save, [type="submit"]');
        if (saveBtn) saveBtn.click();
    }
});

// ==================== RESPONSIVIDADE ====================
window.addEventListener('resize', function() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar && window.innerWidth > 768) {
        sidebar.classList.remove('active');
    }
});

// Export para uso em outros arquivos
window.GeRot = {
    openModal,
    closeModal,
    showNotification,
    showLoading,
    hideLoading,
    apiRequest,
    formatDate,
    formatTime
}; 