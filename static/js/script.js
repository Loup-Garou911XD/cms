// JavaScript for the Classroom Management System

// Document ready function
document.addEventListener('DOMContentLoaded', function() {
    console.log('Classroom Management System loaded');
    
    // Add event listeners to form elements
    setupFormValidation();
    
    // Setup any interactive elements
    setupInteractiveElements();
});

// Form validation
function setupFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            let isValid = true;
            const requiredFields = form.querySelectorAll('[required]');
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('is-invalid');
                } else {
                    field.classList.remove('is-invalid');
                }
            });
            
            if (!isValid) {
                event.preventDefault();
                alert('Please fill out all required fields');
            }
        });
    });
}

// Setup interactive elements
function setupInteractiveElements() {
    // Toggle visibility of advanced search options
    const advancedSearchToggle = document.getElementById('advanced-search-toggle');
    if (advancedSearchToggle) {
        const advancedOptions = document.getElementById('advanced-search-options');
        advancedSearchToggle.addEventListener('click', function() {
            if (advancedOptions.style.display === 'none') {
                advancedOptions.style.display = 'block';
                this.textContent = 'Hide Advanced Options';
            } else {
                advancedOptions.style.display = 'none';
                this.textContent = 'Show Advanced Options';
            }
        });
    }
    
    // Highlight current page in navigation
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}
