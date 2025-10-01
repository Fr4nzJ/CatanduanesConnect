// Form Validation
function validateForm(form) {
    if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
    }
    form.classList.add('was-validated');
}

// Initialize all forms with validation
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            validateForm(this);
        });
    });
});

// Password Strength Meter
function checkPasswordStrength(password) {
    let strength = 0;
    
    // Length check
    if (password.length >= 8) strength += 1;
    
    // Contains number
    if (/\d/.test(password)) strength += 1;
    
    // Contains lowercase
    if (/[a-z]/.test(password)) strength += 1;
    
    // Contains uppercase
    if (/[A-Z]/.test(password)) strength += 1;
    
    // Contains special character
    if (/[^A-Za-z0-9]/.test(password)) strength += 1;
    
    return strength;
}

// Update password strength meter
function updatePasswordStrength(input) {
    const strength = checkPasswordStrength(input.value);
    const meter = document.getElementById('password-strength-meter');
    const feedback = document.getElementById('password-strength-feedback');
    
    if (meter && feedback) {
        meter.value = strength;
        
        switch(strength) {
            case 0:
            case 1:
                feedback.textContent = 'Very Weak';
                feedback.className = 'text-danger';
                break;
            case 2:
                feedback.textContent = 'Weak';
                feedback.className = 'text-warning';
                break;
            case 3:
                feedback.textContent = 'Medium';
                feedback.className = 'text-info';
                break;
            case 4:
                feedback.textContent = 'Strong';
                feedback.className = 'text-primary';
                break;
            case 5:
                feedback.textContent = 'Very Strong';
                feedback.className = 'text-success';
                break;
        }
    }
}

// Confirm Password Match
function checkPasswordMatch() {
    const password = document.getElementById('password');
    const confirmPassword = document.getElementById('confirm_password');
    const feedback = document.getElementById('password-match-feedback');
    
    if (password && confirmPassword && feedback) {
        if (password.value !== confirmPassword.value) {
            feedback.textContent = 'Passwords do not match';
            feedback.className = 'text-danger';
            return false;
        } else {
            feedback.textContent = 'Passwords match';
            feedback.className = 'text-success';
            return true;
        }
    }
    return true;
}

// Initialize password strength and match checks
document.addEventListener('DOMContentLoaded', function() {
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirm_password');
    
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            updatePasswordStrength(this);
        });
    }
    
    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener('input', checkPasswordMatch);
    }
});

// Flash Message Auto-dismiss
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.classList.remove('show');
            setTimeout(() => message.remove(), 150);
        }, 5000);
    });
});

// Mobile Navigation Toggle
document.addEventListener('DOMContentLoaded', function() {
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    
    if (navbarToggler && navbarCollapse) {
        navbarToggler.addEventListener('click', function() {
            navbarCollapse.classList.toggle('show');
        });
        
        // Close mobile menu when clicking outside
        document.addEventListener('click', function(event) {
            if (!navbarCollapse.contains(event.target) && !navbarToggler.contains(event.target)) {
                navbarCollapse.classList.remove('show');
            }
        });
    }
});

// Smooth Scroll
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
}); 