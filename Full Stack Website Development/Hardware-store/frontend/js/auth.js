class Auth {
    constructor() {
        this.currentUser = null;
        this.init();
    }

    async init() {
        const token = localStorage.getItem('token');
        if (token) {
            try {
                api.setToken(token);
                const response = await api.getCurrentUser();
                this.currentUser = response.user;
                this.onAuthStateChange(true);
            } catch (error) {
                console.error('Auth initialization failed:', error);
                this.logout();
            }
        } else {
            this.onAuthStateChange(false);
        }
    }

    async login(email, password) {
        try {
            const response = await api.login({ email, password });
            api.setToken(response.token);
            this.currentUser = response.user;
            this.onAuthStateChange(true);
            this.showMessage('Login successful!', 'success');
            return { success: true, user: response.user };
        } catch (error) {
            this.showMessage('Login failed: ' + error.message, 'error');
            return { success: false, message: error.message };
        }
    }

    async register(username, email, password) {
        try {
            const response = await api.register({ username, email, password });
            api.setToken(response.token);
            this.currentUser = response.user;
            this.onAuthStateChange(true);
            this.showMessage('Registration successful!', 'success');
            return { success: true, user: response.user };
        } catch (error) {
            this.showMessage('Registration failed: ' + error.message, 'error');
            return { success: false, message: error.message };
        }
    }

    logout() {
        this.currentUser = null;
        api.setToken(null);
        
        // Clear all localStorage data except contact messages
        localStorage.removeItem('token');
        localStorage.removeItem('adminAuth');
        localStorage.removeItem('rohit_hardware_cart');
        
        this.onAuthStateChange(false);
        this.showMessage('Logged out successfully!', 'success');
        
        // Force a complete page reload to reset all states
        setTimeout(() => {
            // Check if we're on cart page or admin page
            const currentPath = window.location.pathname;
            const isCartPage = currentPath.includes('cart.html');
            const isAdminPage = currentPath.includes('admin.html');
            
            if (isCartPage || isAdminPage) {
                // Redirect to home page
                window.location.href = 'index.html';
            } else {
                // Reload current page
                window.location.reload();
            }
        }, 1000);
    }

    isAuthenticated() {
        return this.currentUser !== null;
    }

    isAdmin() {
        return this.currentUser && this.currentUser.role === 'admin';
    }

    onAuthStateChange(authenticated) {
        // Dispatch custom event for other components to listen to
        const event = new CustomEvent('authStateChange', {
            detail: { authenticated, user: this.currentUser }
        });
        document.dispatchEvent(event);

        // Update UI elements
        this.updateAuthUI();
    }

    updateAuthUI() {
        const loginBtn = document.getElementById('loginBtn');
        const registerBtn = document.getElementById('registerBtn');
        const logoutBtn = document.getElementById('logoutBtn');
        const mobileLoginBtn = document.getElementById('mobileLoginBtn');
        const mobileRegisterBtn = document.getElementById('mobileRegisterBtn');
        const mobileLogoutBtn = document.getElementById('mobileLogoutBtn');
        const adminWelcome = document.getElementById('adminWelcome');

        if (this.isAuthenticated()) {
            if (loginBtn) loginBtn.style.display = 'none';
            if (registerBtn) registerBtn.style.display = 'none';
            if (logoutBtn) logoutBtn.style.display = 'inline-block';
            if (mobileLoginBtn) mobileLoginBtn.style.display = 'none';
            if (mobileRegisterBtn) mobileRegisterBtn.style.display = 'none';
            if (mobileLogoutBtn) mobileLogoutBtn.style.display = 'inline-block';
            
            if (adminWelcome && this.isAdmin()) {
                adminWelcome.textContent = `Welcome, ${this.currentUser.username}`;
            }

            // Update cart count
            this.updateCartCount();
        } else {
            if (loginBtn) loginBtn.style.display = 'inline-block';
            if (registerBtn) registerBtn.style.display = 'inline-block';
            if (logoutBtn) logoutBtn.style.display = 'none';
            if (mobileLoginBtn) mobileLoginBtn.style.display = 'inline-block';
            if (mobileRegisterBtn) mobileRegisterBtn.style.display = 'inline-block';
            if (mobileLogoutBtn) mobileLogoutBtn.style.display = 'none';
            
            // Reset cart count for non-authenticated users
            const cartCount = document.querySelector('.cart-count');
            const mobileCartCount = document.querySelector('.mobile-cart-count');
            if (cartCount) cartCount.textContent = '0';
            if (mobileCartCount) mobileCartCount.textContent = '0';
        }
    }

    async updateCartCount() {
        if (!this.isAuthenticated()) return;

        try {
            const cart = await api.getCart();
            const cartCount = document.querySelector('.cart-count');
            const mobileCartCount = document.querySelector('.mobile-cart-count');
            
            if (cartCount || mobileCartCount) {
                const totalItems = cart.items ? cart.items.reduce((sum, item) => sum + item.quantity, 0) : 0;
                if (cartCount) cartCount.textContent = totalItems;
                if (mobileCartCount) mobileCartCount.textContent = totalItems;
            }
        } catch (error) {
            console.error('Failed to update cart count:', error);
        }
    }

    showMessage(message, type) {
        // Remove existing messages
        const existingMessage = document.querySelector('.message');
        if (existingMessage) {
            existingMessage.remove();
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.textContent = message;
        messageDiv.style.cssText = `
            position: fixed;
            top: 100px;
            left: 50%;
            transform: translateX(-50%);
            padding: 15px 25px;
            border-radius: 8px;
            font-weight: 600;
            z-index: 2001;
            max-width: 90%;
            text-align: center;
            background: ${type === 'success' ? '#10b981' : '#ef4444'};
            color: white;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
        `;

        document.body.appendChild(messageDiv);

        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.remove();
            }
        }, 5000);
    }

    // Check authentication and redirect if needed
    requireAuth(redirectUrl = 'index.html') {
        if (!this.isAuthenticated()) {
            this.showMessage('Please login to access this page', 'error');
            setTimeout(() => {
                window.location.href = redirectUrl;
            }, 1500);
            return false;
        }
        return true;
    }

    // Check admin privileges and redirect if needed
    requireAdmin(redirectUrl = 'index.html') {
        if (!this.isAuthenticated() || !this.isAdmin()) {
            this.showMessage('Admin access required', 'error');
            setTimeout(() => {
                window.location.href = redirectUrl;
            }, 1500);
            return false;
        }
        return true;
    }

    // Show auth modal
    showAuthModal(tab = 'login') {
        const authModal = document.getElementById('authModal');
        if (authModal) {
            authModal.style.display = 'block';
            // Switch to specified tab
            const event = new CustomEvent('showAuthTab', { detail: { tab } });
            document.dispatchEvent(event);
        }
    }
}

const auth = new Auth();

// Listen for show auth tab events
document.addEventListener('showAuthTab', (event) => {
    if (window.showAuthTab) {
        showAuthTab(event.detail.tab);
    }
});

// Make auth globally available
window.auth = auth;