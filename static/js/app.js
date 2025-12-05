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
