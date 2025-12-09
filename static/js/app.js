document.addEventListener('DOMContentLoaded', () => {
    autoDismissAlerts();
    enableAutoSubmit();
    enableCopyButtons();
});

function autoDismissAlerts() {
    document.querySelectorAll('.alert').forEach((alert) => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.3s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 350);
        }, 5000);
    });
}

function enableAutoSubmit() {
    document.querySelectorAll('[data-auto-submit]').forEach((element) => {
        element.addEventListener('change', () => {
            element.form?.submit();
        });
    });
}

function enableCopyButtons() {
    document.querySelectorAll('[data-copy]').forEach((button) => {
        button.addEventListener('click', () => {
            const target = document.querySelector(button.dataset.copy);
            if (target) {
                navigator.clipboard.writeText(target.textContent.trim()).then(() => {
                    button.classList.add('copied');
                    setTimeout(() => button.classList.remove('copied'), 1500);
                });
            }
        });
    });
}

// Sidebar Toggle
const sidebarToggle = document.getElementById('sidebar-toggle');
const sidebar = document.getElementById('sidebar');
const mainContent = document.getElementById('main-content');

if (sidebarToggle && sidebar && mainContent) {
    sidebarToggle.addEventListener('click', (e) => {
        e.preventDefault();
        sidebar.classList.toggle('active');
        mainContent.classList.toggle('sidebar-active');
    });
}
