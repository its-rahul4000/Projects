// Main application initialization
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initAuth();
    initProducts();
    initCart();
    initNavigation();
    initModals();
    initContactForm();
    initFloatingContact();
    
    console.log('Rohit Hardware Store initialized');
});

function initAuth() {
    // Auth modal functionality
    const authModal = document.getElementById('authModal');
    const loginBtn = document.getElementById('loginBtn');
    const registerBtn = document.getElementById('registerBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    const mobileLoginBtn = document.getElementById('mobileLoginBtn');
    const mobileRegisterBtn = document.getElementById('mobileRegisterBtn');
    const mobileLogoutBtn = document.getElementById('mobileLogoutBtn');
    const closeModal = document.querySelector('#authModal .close');

    // Open auth modal
    if (loginBtn) {
        loginBtn.addEventListener('click', () => {
            if (authModal) {
                authModal.style.display = 'block';
                showAuthTab('login');
            }
        });
    }

    if (registerBtn) {
        registerBtn.addEventListener('click', () => {
            if (authModal) {
                authModal.style.display = 'block';
                showAuthTab('register');
            }
        });
    }

    if (mobileLoginBtn) {
        mobileLoginBtn.addEventListener('click', () => {
            if (authModal) {
                authModal.style.display = 'block';
                showAuthTab('login');
                closeMobileMenu();
            }
        });
    }

    if (mobileRegisterBtn) {
        mobileRegisterBtn.addEventListener('click', () => {
            if (authModal) {
                authModal.style.display = 'block';
                showAuthTab('register');
                closeMobileMenu();
            }
        });
    }

    // Logout
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            auth.logout();
        });
    }

    if (mobileLogoutBtn) {
        mobileLogoutBtn.addEventListener('click', () => {
            auth.logout();
            closeMobileMenu();
        });
    }

    // Close modal
    if (closeModal) {
        closeModal.addEventListener('click', () => {
            if (authModal) {
                authModal.style.display = 'none';
                resetAuthForms();
            }
        });
    }

    // Auth tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.getAttribute('data-tab');
            showAuthTab(tab);
        });
    });

    // Password toggle functionality
    initPasswordToggles();

    // Auth form submissions
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await handleLogin();
        });
    }

    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await handleRegister();
        });
    }

    // Listen for auth state changes
    document.addEventListener('authStateChange', (event) => {
        const { authenticated, user } = event.detail;
        console.log('Auth state changed:', authenticated, user);
        
        // Update UI based on auth state
        updateUIForAuthState(authenticated, user);
        
        // Close auth modal if user becomes authenticated
        if (authenticated && authModal && authModal.style.display === 'block') {
            authModal.style.display = 'none';
            resetAuthForms();
        }
    });
}

function initPasswordToggles() {
    // Toggle password visibility
    const toggleLoginPassword = document.getElementById('toggleLoginPassword');
    const toggleRegisterPassword = document.getElementById('toggleRegisterPassword');
    const toggleConfirmPassword = document.getElementById('toggleConfirmPassword');

    if (toggleLoginPassword) {
        toggleLoginPassword.addEventListener('click', () => {
            togglePasswordVisibility('loginPassword', toggleLoginPassword);
        });
    }

    if (toggleRegisterPassword) {
        toggleRegisterPassword.addEventListener('click', () => {
            togglePasswordVisibility('registerPassword', toggleRegisterPassword);
        });
    }

    if (toggleConfirmPassword) {
        toggleConfirmPassword.addEventListener('click', () => {
            togglePasswordVisibility('confirmPassword', toggleConfirmPassword);
        });
    }
}

function togglePasswordVisibility(inputId, toggleIcon) {
    const input = document.getElementById(inputId);
    if (!input) return;
    
    const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
    input.setAttribute('type', type);
    
    // Update icon
    if (toggleIcon) {
        toggleIcon.classList.toggle('fa-eye');
        toggleIcon.classList.toggle('fa-eye-slash');
    }
}

async function handleLogin() {
    const email = document.getElementById('loginEmail');
    const password = document.getElementById('loginPassword');
    const submitBtn = document.querySelector('#loginForm .btn-auth-submit');
    
    if (!email || !password || !submitBtn) return;
    
    const emailValue = email.value;
    const passwordValue = password.value;
    
    // Show loading state
    submitBtn.classList.add('loading');
    submitBtn.disabled = true;

    try {
        const result = await auth.login(emailValue, passwordValue);
        
        if (result.success) {
            // Success handled by auth state change
        } else {
            // Show error on form
            password.classList.add('auth-error');
        }
    } catch (error) {
        console.error('Login error:', error);
    } finally {
        // Remove loading state
        submitBtn.classList.remove('loading');
        submitBtn.disabled = false;
    }
}

async function handleRegister() {
    const username = document.getElementById('registerUsername');
    const email = document.getElementById('registerEmail');
    const password = document.getElementById('registerPassword');
    const confirmPassword = document.getElementById('confirmPassword');
    const submitBtn = document.querySelector('#registerForm .btn-auth-submit');
    const acceptTerms = document.getElementById('acceptTerms');

    if (!username || !email || !password || !confirmPassword || !submitBtn || !acceptTerms) {
        return;
    }

    const usernameValue = username.value;
    const emailValue = email.value;
    const passwordValue = password.value;
    const confirmPasswordValue = confirmPassword.value;

    // Validate passwords match
    if (passwordValue !== confirmPasswordValue) {
        auth.showMessage('Passwords do not match', 'error');
        confirmPassword.classList.add('auth-error');
        return;
    }

    // Validate terms accepted
    if (!acceptTerms.checked) {
        auth.showMessage('Please accept the terms and conditions', 'error');
        return;
    }

    // Show loading state
    submitBtn.classList.add('loading');
    submitBtn.disabled = true;

    try {
        const result = await auth.register(usernameValue, emailValue, passwordValue);
        
        if (result.success) {
            // Success handled by auth state change
        } else {
            // Show error on form
            email.classList.add('auth-error');
        }
    } catch (error) {
        console.error('Registration error:', error);
    } finally {
        // Remove loading state
        submitBtn.classList.remove('loading');
        submitBtn.disabled = false;
    }
}

function resetAuthForms() {
    // Reset all auth forms
    const forms = document.querySelectorAll('#loginForm, #registerForm');
    forms.forEach(form => {
        if (form) {
            form.reset();
            // Remove error states
            form.querySelectorAll('.auth-error').forEach(el => {
                el.classList.remove('auth-error');
            });
        }
    });
}

function showAuthTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    const activeTabBtn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
    if (activeTabBtn) {
        activeTabBtn.classList.add('active');
    }

    // Update tab content
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
    });
    const activePane = document.getElementById(tabName);
    if (activePane) {
        activePane.classList.add('active');
    }

    // Reset forms when switching tabs
    resetAuthForms();
}

function initProducts() {
    // Load featured and sale products
    if (window.productManager) {
        productManager.loadFeaturedProducts();
        productManager.loadSaleProducts();
    }

    // Category navigation
    const categoryCards = document.querySelectorAll('.category-card');
    categoryCards.forEach(card => {
        card.addEventListener('click', (e) => {
            e.preventDefault();
            const category = card.getAttribute('data-category');
            if (category && window.productManager) {
                productManager.loadProductsByCategory(category);
            }
        });
    });

    // Setup dropdown category links
    document.addEventListener('click', (e) => {
        if (e.target.matches('.dropdown-menu a, .sidebar-dropdown-menu a, .footer-section a[data-category]')) {
            e.preventDefault();
            const category = e.target.getAttribute('data-category');
            if (category && window.productManager) {
                productManager.loadProductsByCategory(category);
                closeMobileMenu();
            }
        }
    });

    // Search functionality
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');

    const performSearch = (searchTerm) => {
        if (searchTerm && searchTerm.trim() !== '' && window.productManager) {
            productManager.searchProducts(searchTerm.trim());
        } else if (window.productManager) {
            productManager.loadFeaturedProducts();
        }
    };

    if (searchInput && searchBtn) {
        searchBtn.addEventListener('click', () => {
            performSearch(searchInput.value);
        });
        
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performSearch(searchInput.value);
            }
        });
    }

    // Hero section buttons
    const shopNowBtn = document.getElementById('shopNowBtn');
    const viewSaleBtn = document.getElementById('viewSaleBtn');

    if (shopNowBtn) {
        shopNowBtn.addEventListener('click', () => {
            const featuredSection = document.getElementById('featured');
            if (featuredSection) {
                featuredSection.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }

    if (viewSaleBtn) {
        viewSaleBtn.addEventListener('click', () => {
            const saleSection = document.getElementById('sale');
            if (saleSection) {
                saleSection.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }
}

function initCart() {
    // Cart functionality is handled by cart.js
    // This function ensures cart is initialized on pages that need it
    if (typeof cartManager !== 'undefined' && typeof cartManager.init === 'function') {
        // Cart is initialized in its own file
    }
}

function initNavigation() {
    // Mobile menu functionality
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const mobileSidebar = document.querySelector('.mobile-sidebar');
    const sidebarOverlay = document.querySelector('.sidebar-overlay');
    const sidebarClose = document.querySelector('.sidebar-close');

    function openMobileMenu() {
        if (mobileSidebar) {
            mobileSidebar.classList.add('active');
        }
        if (sidebarOverlay) {
            sidebarOverlay.classList.add('active');
        }
        document.body.style.overflow = 'hidden';
    }

    function closeMobileMenu() {
        if (mobileSidebar) {
            mobileSidebar.classList.remove('active');
        }
        if (sidebarOverlay) {
            sidebarOverlay.classList.remove('active');
        }
        document.body.style.overflow = '';
    }

    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', openMobileMenu);
    }

    if (sidebarClose) {
        sidebarClose.addEventListener('click', closeMobileMenu);
    }

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', closeMobileMenu);
    }

    // Mobile dropdown functionality
    const dropdownToggles = document.querySelectorAll('.sidebar-dropdown .dropdown-toggle');
    dropdownToggles.forEach(toggle => {
        toggle.addEventListener('click', (e) => {
            e.preventDefault();
            const dropdownMenu = toggle.nextElementSibling;
            if (dropdownMenu) {
                dropdownMenu.classList.toggle('active');
            }
        });
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const target = document.querySelector(targetId);
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                closeMobileMenu();
            }
        });
    });

    // Active navigation highlighting
    const sections = document.querySelectorAll('section[id]');
    const navItems = document.querySelectorAll('.nav-links a');

    function highlightNavigation() {
        const scrollY = window.pageYOffset;

        sections.forEach(section => {
            const sectionHeight = section.offsetHeight;
            const sectionTop = section.offsetTop - 100;
            const sectionId = section.getAttribute('id');

            if (scrollY > sectionTop && scrollY <= sectionTop + sectionHeight) {
                navItems.forEach(item => {
                    item.classList.remove('active');
                    if (item.getAttribute('href') === `#${sectionId}`) {
                        item.classList.add('active');
                    }
                });
            }
        });
    }

    window.addEventListener('scroll', highlightNavigation);
}

function initModals() {
    // Close modals when clicking outside
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    });

    // Quick view modal close
    const quickViewClose = document.querySelector('#quickViewModal .close');
    if (quickViewClose) {
        quickViewClose.addEventListener('click', () => {
            if (window.productManager && productManager.closeQuickView) {
                productManager.closeQuickView();
            }
        });
    }

    // Product modal close
    const productModalClose = document.querySelector('#productModal .close');
    if (productModalClose) {
        productModalClose.addEventListener('click', () => {
            if (window.productManager && productManager.closeModal) {
                productManager.closeModal();
            }
        });
    }
}

function initContactForm() {
    const contactForm = document.getElementById('contactForm');
    if (contactForm) {
        contactForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Get form values
            const name = document.getElementById('contactName').value;
            const email = document.getElementById('contactEmail').value;
            const subject = document.getElementById('contactSubject').value;
            const message = document.getElementById('contactMessage').value;
            const submitBtn = document.getElementById('contactSubmitBtn');
            
            // Simple form validation
            if (!name || !email || !subject || !message) {
                auth.showMessage('Please fill in all required fields', 'error');
                return;
            }

            // Show loading state
            submitBtn.disabled = true;
            submitBtn.textContent = 'Sending...';
            
            try {
                // Send contact data to backend
                const response = await fetch('http://localhost:3000/api/contact', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        name: name,
                        email: email,
                        subject: subject,
                        message: message
                    })
                });

                if (response.ok) {
                    const result = await response.json();
                    
                    if (result.success) {
                        auth.showMessage('Thank you for your message! We will get back to you soon.', 'success');
                        contactForm.reset();
                        
                        // Message is now stored in backend and can be viewed in admin panel
                        console.log('✅ Contact message saved to admin panel');
                        
                        // Store in localStorage as backup
                        const messageData = {
                            id: result.messageId || Date.now().toString(),
                            name,
                            email,
                            subject,
                            message,
                            status: 'unread',
                            date: new Date().toISOString()
                        };
                        
                        // Save to localStorage for admin panel access
                        let existingMessages = JSON.parse(localStorage.getItem('hardwareStoreContactMessages') || '[]');
                        existingMessages.unshift(messageData);
                        localStorage.setItem('hardwareStoreContactMessages', JSON.stringify(existingMessages));
                        
                    } else {
                        throw new Error(result.message || 'Failed to send message');
                    }
                } else {
                    throw new Error('Failed to send message');
                }
            } catch (error) {
                auth.showMessage('Error sending message: ' + error.message, 'error');
                console.error('Contact form error:', error);
                
                // Fallback: Save to localStorage if backend fails
                const messageData = {
                    id: Date.now().toString(),
                    name,
                    email,
                    subject,
                    message,
                    status: 'unread',
                    date: new Date().toISOString()
                };
                
                let existingMessages = JSON.parse(localStorage.getItem('hardwareStoreContactMessages') || '[]');
                existingMessages.unshift(messageData);
                localStorage.setItem('hardwareStoreContactMessages', JSON.stringify(existingMessages));
                
                auth.showMessage('Message saved locally. Will sync with admin panel.', 'warning');
                contactForm.reset();
            } finally {
                // Reset button state
                submitBtn.disabled = false;
                submitBtn.textContent = 'Send Message';
            }
        });
    }
}

function initFloatingContact() {
    const floatingContact = document.querySelector('.floating-contact');
    if (floatingContact) {
        // Add hover effects
        floatingContact.addEventListener('mouseenter', () => {
            floatingContact.classList.add('hover');
        });

        floatingContact.addEventListener('mouseleave', () => {
            floatingContact.classList.remove('hover');
        });
    }
}

function updateUIForAuthState(authenticated, user) {
    // This function can be expanded to update various parts of the UI
    // based on authentication state
    console.log('Updating UI for auth state:', authenticated);
}

// Export to global scope for HTML onclick handlers
window.showAuthTab = showAuthTab;
window.closeMobileMenu = function() {
    const mobileSidebar = document.querySelector('.mobile-sidebar');
    const sidebarOverlay = document.querySelector('.sidebar-overlay');
    if (mobileSidebar) mobileSidebar.classList.remove('active');
    if (sidebarOverlay) sidebarOverlay.classList.remove('active');
    document.body.style.overflow = '';
};