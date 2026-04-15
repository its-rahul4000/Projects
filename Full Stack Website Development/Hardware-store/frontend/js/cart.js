class CartManager {
    constructor() {
        this.cart = {
            items: [],
            subtotal: 0,
            shipping: 0,
            tax: 0,
            total: 0
        };
        this.currentStep = 1;
        this.localCartKey = 'rohit_hardware_cart';
    }

    async init() {
        await this.loadCart();
        await this.loadSuggestedProducts();
        this.setupCartNavigation();
        
        // Initialize checkout functionality
        this.initCheckoutFunctionality();
    }

    async loadCart() {
        try {
            // Always check localStorage first for cart data
            const localCart = localStorage.getItem(this.localCartKey);
            
            if (localCart) {
                this.cart = JSON.parse(localCart);
            } else {
                this.cart = { items: [], subtotal: 0, shipping: 0, tax: 0, total: 0 };
            }
            
            // If user is logged in, try to sync with backend
            if (auth.isAuthenticated()) {
                try {
                    const serverCart = await api.getCart();
                    // Merge local and server cart
                    if (serverCart && serverCart.items && serverCart.items.length > 0) {
                        this.cart = serverCart;
                        this.saveToLocalStorage();
                    }
                } catch (error) {
                    console.log('Using local cart data:', error.message);
                }
            }
            
            this.renderCart();
            this.updateSummary();
            this.updateCheckoutButton();
            this.updateCartCount();
            
        } catch (error) {
            console.error('Error loading cart:', error);
            this.showEmptyCart();
        }
    }

    saveToLocalStorage() {
        try {
            localStorage.setItem(this.localCartKey, JSON.stringify(this.cart));
        } catch (error) {
            console.error('Error saving cart to localStorage:', error);
        }
    }

    renderCart() {
        const container = document.getElementById('cartItems');
        const emptyCart = document.getElementById('emptyCart');

        if (!container) return;

        if (!this.cart.items || this.cart.items.length === 0) {
            this.showEmptyCart();
            return;
        }

        if (emptyCart) {
            emptyCart.style.display = 'none';
        }

        container.innerHTML = this.cart.items.map(item => this.createCartItem(item)).join('');
    }

    createCartItem(item) {
        const product = item.product || item;
        const productId = product._id || product.id;
        const quantity = item.quantity || 1;
        const price = product.salePrice || product.price || 0;
        const total = price * quantity;

        return `
            <div class="cart-item" data-product-id="${productId}">
                <div class="cart-item-image">
                    <img src="${product.image || 'https://images.unsplash.com/photo-1581094794329-c8112a89af12?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'}" 
                         alt="${product.name || 'Product'}" 
                         onerror="this.src='https://images.unsplash.com/photo-1581094794329-c8112a89af12?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'">
                </div>
                <div class="cart-item-details">
                    <h3 class="cart-item-name">${product.name || 'Product'}</h3>
                    <div class="cart-item-category">${product.category || ''}</div>
                    <div class="cart-item-price">₹${price.toFixed(2)} each</div>
                    <div class="cart-item-actions">
                        <div class="quantity-controls">
                            <button class="quantity-btn" onclick="cartManager.updateQuantity('${productId}', ${quantity - 1})">-</button>
                            <input type="number" class="quantity-input" value="${quantity}" min="1" 
                                   onchange="cartManager.updateQuantity('${productId}', parseInt(this.value))">
                            <button class="quantity-btn" onclick="cartManager.updateQuantity('${productId}', ${quantity + 1})">+</button>
                        </div>
                        <button class="btn btn-danger remove-btn" onclick="cartManager.removeItem('${productId}')">
                            <i class="fas fa-trash"></i> Remove
                        </button>
                    </div>
                </div>
                <div class="cart-item-total">
                    <div class="cart-item-total-price">₹${total.toFixed(2)}</div>
                </div>
            </div>
        `;
    }

    showEmptyCart() {
        const container = document.getElementById('cartItems');
        const emptyCart = document.getElementById('emptyCart');
        
        if (container) {
            container.innerHTML = '';
        }
        
        if (emptyCart) {
            emptyCart.style.display = 'block';
        }

        this.updateSummary();
        this.updateCheckoutButton();
        this.updateCartCount();
    }

    async updateQuantity(productId, newQuantity) {
        if (newQuantity < 1) {
            await this.removeItem(productId);
            return;
        }

        // Find product in cart
        const itemIndex = this.cart.items.findIndex(item => {
            const itemProduct = item.product || item;
            return (itemProduct._id === productId) || (itemProduct.id === productId);
        });
        
        if (itemIndex > -1) {
            // Update quantity
            this.cart.items[itemIndex].quantity = newQuantity;
            
            // Save to localStorage
            this.saveToLocalStorage();
            
            // If logged in, try to update backend
            if (auth.isAuthenticated()) {
                try {
                    await api.updateCartItem(productId, newQuantity);
                } catch (error) {
                    console.log('Could not update cart on server:', error);
                }
            }
            
            // Update display
            this.updateSummary();
            this.renderCart();
            this.updateCartCount();
        }
    }

    async removeItem(productId) {
        // Remove from local cart
        this.cart.items = this.cart.items.filter(item => {
            const itemProduct = item.product || item;
            return (itemProduct._id !== productId) && (itemProduct.id !== productId);
        });
        
        // Save to localStorage
        this.saveToLocalStorage();
        
        // If logged in, try to remove from backend
        if (auth.isAuthenticated()) {
            try {
                await api.removeFromCart(productId);
            } catch (error) {
                console.log('Could not remove from server cart:', error);
            }
        }
        
        // Update display
        this.updateSummary();
        this.renderCart();
        this.updateCartCount();
        
        this.showMessage('Item removed from cart', 'success');
    }

    async addToCart(product, quantity = 1) {
        const productId = product._id || product.id;
        
        // Check if already in cart
        const existingItemIndex = this.cart.items.findIndex(item => {
            const itemProduct = item.product || item;
            return (itemProduct._id === productId) || (itemProduct.id === productId);
        });
        
        if (existingItemIndex > -1) {
            // Update quantity
            this.cart.items[existingItemIndex].quantity += quantity;
        } else {
            // Add new item
            this.cart.items.push({
                product: product,
                quantity: quantity
            });
        }
        
        // Save to localStorage
        this.saveToLocalStorage();
        
        // If logged in, try to add to backend
        if (auth.isAuthenticated()) {
            try {
                await api.addToCart(productId, quantity);
            } catch (error) {
                console.log('Could not add to server cart:', error);
            }
        }
        
        // Update UI
        this.updateSummary();
        this.renderCart();
        this.updateCartCount();
        
        this.showMessage('Product added to cart!', 'success');
    }

    updateSummary() {
        // Recalculate totals
        let subtotal = 0;
        this.cart.items.forEach(item => {
            const product = item.product || item;
            const price = product.salePrice || product.price || 0;
            subtotal += price * (item.quantity || 1);
        });
        
        const shipping = subtotal > 500 ? 0 : 50;
        const tax = subtotal * 0.08;
        const total = subtotal + shipping + tax;
        
        // Update cart object
        this.cart.subtotal = subtotal;
        this.cart.shipping = shipping;
        this.cart.tax = tax;
        this.cart.total = total;
        
        // Update display elements
        const elements = {
            'subtotal': `₹${subtotal.toFixed(2)}`,
            'shipping': `₹${shipping.toFixed(2)}`,
            'tax': `₹${tax.toFixed(2)}`,
            'total': `₹${total.toFixed(2)}`,
            'reviewSubtotal': `₹${subtotal.toFixed(2)}`,
            'reviewShipping': `₹${shipping.toFixed(2)}`,
            'reviewTax': `₹${tax.toFixed(2)}`,
            'reviewTotal': `₹${total.toFixed(2)}`
        };
        
        Object.keys(elements).forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = elements[id];
            }
        });

        // Update free shipping message
        const shippingNote = document.getElementById('shippingNote');
        const freeShippingRemaining = document.getElementById('freeShippingRemaining');
        
        if (shippingNote && freeShippingRemaining) {
            if (subtotal < 500) {
                const remaining = (500 - subtotal).toFixed(2);
                freeShippingRemaining.textContent = remaining;
                shippingNote.style.display = 'flex';
            } else {
                shippingNote.style.display = 'none';
            }
        }
    }

    updateCartCount() {
        const totalItems = this.cart.items.reduce((sum, item) => sum + (item.quantity || 1), 0);
        
        // Update all cart count elements
        const cartCountElements = document.querySelectorAll('.cart-count, .mobile-cart-count');
        cartCountElements.forEach(element => {
            element.textContent = totalItems;
        });
    }

    updateCheckoutButton() {
        const checkoutBtn = document.getElementById('checkoutBtn');
        if (checkoutBtn) {
            checkoutBtn.disabled = !this.cart.items || this.cart.items.length === 0;
        }
    }

    async loadSuggestedProducts() {
        try {
            // Try to get from API
            let products = [];
            try {
                const response = await api.getProducts({ limit: 4 });
                products = response.products || [];
            } catch (error) {
                // Fallback to localStorage products
                const savedProducts = localStorage.getItem('hardwareStoreProducts');
                if (savedProducts) {
                    products = JSON.parse(savedProducts).slice(0, 4);
                }
            }
            
            this.renderSuggestedProducts(products);
        } catch (error) {
            console.error('Error loading suggested products:', error);
        }
    }

    renderSuggestedProducts(products) {
        const container = document.getElementById('suggestedProducts');
        if (!container) return;

        if (!products || products.length === 0) {
            container.innerHTML = '<p class="no-data">No suggestions available</p>';
            return;
        }

        container.innerHTML = products.map(product => `
            <div class="product-card">
                <div class="product-image">
                    <img src="${product.image || 'https://images.unsplash.com/photo-1581094794329-c8112a89af12?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'}" 
                         alt="${product.name}" 
                         onerror="this.src='https://images.unsplash.com/photo-1581094794329-c8112a89af12?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'">
                </div>
                <div class="product-info">
                    <h3 class="product-name">${product.name}</h3>
                    <div class="product-price">
                        <span class="current-price">₹${(product.price || 0).toFixed(2)}</span>
                        ${product.onSale && product.discount ? `
                            <span class="original-price">₹${(product.originalPrice || product.price).toFixed(2)}</span>
                            <span class="discount">-${product.discount}%</span>
                        ` : ''}
                    </div>
                    <button class="btn-add-cart" onclick="cartManager.addToCart(${JSON.stringify(product).replace(/"/g, '&quot;')})">
                        <i class="fas fa-shopping-cart"></i> Add to Cart
                    </button>
                </div>
            </div>
        `).join('');
    }

    setupCartNavigation() {
        // Fix category button in cart page
        document.addEventListener('click', (e) => {
            // Handle category links
            if (e.target.matches('.dropdown-menu a, .sidebar-dropdown-menu a, .footer-section a[data-category], .category-card')) {
                e.preventDefault();
                const element = e.target.closest('[data-category]');
                if (element) {
                    const category = element.getAttribute('data-category');
                    if (category) {
                        // Redirect to home page with category filter
                        window.location.href = `index.html?category=${encodeURIComponent(category)}`;
                    }
                }
            }
        });

        // Fix search button in cart page
        const searchInput = document.getElementById('searchInput');
        const searchBtn = document.getElementById('searchBtn');
        
        if (searchInput && searchBtn) {
            const performSearch = (searchTerm) => {
                if (searchTerm && searchTerm.trim() !== '') {
                    // Redirect to home page with search
                    window.location.href = `index.html?search=${encodeURIComponent(searchTerm.trim())}`;
                }
            };

            searchBtn.addEventListener('click', () => {
                performSearch(searchInput.value);
            });
            
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    performSearch(searchInput.value);
                }
            });
        }
    }

    initCheckoutFunctionality() {
        const checkoutBtn = document.getElementById('checkoutBtn');
        const checkoutModal = document.getElementById('checkoutModal');
        const closeCheckoutModal = document.querySelector('#checkoutModal .close');
        const nextStepBtn = document.getElementById('nextStepBtn');
        const prevStepBtn = document.getElementById('prevStepBtn');
        const placeOrderBtn = document.getElementById('placeOrderBtn');
        const checkoutForm = document.getElementById('checkoutForm');

        if (checkoutBtn) {
            checkoutBtn.addEventListener('click', () => {
                if (!auth.isAuthenticated()) {
                    auth.showMessage('Please login to checkout', 'error');
                    auth.showAuthModal('login');
                    return;
                }

                if (checkoutModal) {
                    checkoutModal.style.display = 'block';
                    this.initCheckout();
                }
            });
        }

        if (closeCheckoutModal) {
            closeCheckoutModal.addEventListener('click', () => {
                if (checkoutModal) {
                    checkoutModal.style.display = 'none';
                }
            });
        }

        if (nextStepBtn) {
            nextStepBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.nextStep();
            });
        }

        if (prevStepBtn) {
            prevStepBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.prevStep();
            });
        }

        if (placeOrderBtn) {
            placeOrderBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.placeOrder();
            });
        }

        if (checkoutForm) {
            checkoutForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.placeOrder();
            });
        }

        // Payment method changes
        const paymentRadios = document.querySelectorAll('input[name="paymentMethod"]');
        paymentRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                const cardDetails = document.getElementById('cardDetails');
                if (cardDetails) {
                    cardDetails.style.display = 
                        e.target.value === 'credit_card' || e.target.value === 'debit_card' 
                        ? 'block' 
                        : 'none';
                }
            });
        });
    }

    // Checkout functionality
    initCheckout() {
        this.currentStep = 1;
        this.updateCheckoutSteps();
        this.updateCheckoutActions();
    }

    updateCheckoutSteps() {
        document.querySelectorAll('.checkout-step').forEach(step => {
            step.classList.remove('active');
        });
        
        document.querySelectorAll('.step').forEach(step => {
            step.classList.remove('active');
        });

        const currentStep = document.querySelector(`.checkout-step[data-step="${this.currentStep}"]`);
        const currentStepIndicator = document.querySelector(`.step[data-step="${this.currentStep}"]`);
        
        if (currentStep) currentStep.classList.add('active');
        if (currentStepIndicator) currentStepIndicator.classList.add('active');
    }

    updateCheckoutActions() {
        const prevBtn = document.getElementById('prevStepBtn');
        const nextBtn = document.getElementById('nextStepBtn');
        const placeOrderBtn = document.getElementById('placeOrderBtn');

        if (prevBtn) {
            prevBtn.style.display = this.currentStep > 1 ? 'inline-block' : 'none';
        }

        if (nextBtn) {
            nextBtn.style.display = this.currentStep < 3 ? 'inline-block' : 'none';
        }

        if (placeOrderBtn) {
            placeOrderBtn.style.display = this.currentStep === 3 ? 'inline-block' : 'none';
        }
    }

    nextStep() {
        if (this.currentStep < 3) {
            this.currentStep++;
            this.updateCheckoutSteps();
            this.updateCheckoutActions();
            
            if (this.currentStep === 3) {
                this.updateReviewStep();
            }
        }
    }

    prevStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateCheckoutSteps();
            this.updateCheckoutActions();
        }
    }

    updateReviewStep() {
        // Update review items
        const reviewItems = document.getElementById('reviewItems');
        if (reviewItems) {
            reviewItems.innerHTML = this.cart.items.map(item => {
                const product = item.product || item;
                const price = product.salePrice || product.price || 0;
                const total = price * (item.quantity || 1);
                return `
                    <div class="review-item">
                        <span>${product.name || 'Product'} x ${item.quantity || 1}</span>
                        <span>₹${total.toFixed(2)}</span>
                    </div>
                `;
            }).join('');
        }

        // Update shipping address
        const form = document.getElementById('checkoutForm');
        const shippingAddress = document.getElementById('reviewShippingAddress');
        if (form && shippingAddress) {
            const formData = new FormData(form);
            shippingAddress.innerHTML = `
                ${formData.get('fullName') || 'Not provided'}<br>
                ${formData.get('street') || 'Not provided'}<br>
                ${formData.get('city') || 'Not provided'}, ${formData.get('state') || 'Not provided'} ${formData.get('zipCode') || ''}<br>
                ${formData.get('country') || 'India'}
            `;
        }
    }

    async placeOrder() {
        if (!auth.isAuthenticated()) {
            auth.showMessage('Please login to place an order', 'error');
            auth.showAuthModal('login');
            return;
        }

        const form = document.getElementById('checkoutForm');
        const formData = new FormData(form);

        const orderData = {
            items: this.cart.items.map(item => ({
                product: (item.product && item.product._id) || item.productId,
                quantity: item.quantity || 1
            })),
            shippingAddress: {
                street: formData.get('street') || '',
                city: formData.get('city') || '',
                state: formData.get('state') || '',
                zipCode: formData.get('zipCode') || '',
                country: formData.get('country') || 'India'
            },
            billingAddress: {
                street: formData.get('street') || '',
                city: formData.get('city') || '',
                state: formData.get('state') || '',
                zipCode: formData.get('zipCode') || '',
                country: formData.get('country') || 'India'
            },
            paymentMethod: formData.get('paymentMethod') || 'cash_on_delivery',
            notes: formData.get('notes') || ''
        };

        try {
            const order = await api.createOrder(orderData);
            this.showOrderSuccess(order);
            // Clear cart after successful order
            this.cart.items = [];
            this.saveToLocalStorage();
            this.updateSummary();
            this.renderCart();
            this.updateCartCount();
        } catch (error) {
            this.showMessage('Error placing order: ' + error.message, 'error');
        }
    }

    showOrderSuccess(order) {
        // Close checkout modal
        const checkoutModal = document.getElementById('checkoutModal');
        if (checkoutModal) {
            checkoutModal.style.display = 'none';
        }
        
        // Show success modal
        const successModal = document.getElementById('orderSuccessModal');
        const orderNumber = document.getElementById('successOrderNumber');
        const orderTotal = document.getElementById('successOrderTotal');
        
        if (orderNumber) orderNumber.textContent = order.orderNumber || 'N/A';
        if (orderTotal) orderTotal.textContent = `₹${(order.totalAmount || 0).toFixed(2)}`;
        
        if (successModal) {
            successModal.style.display = 'block';
        }
        
        // Set up success modal buttons
        const viewOrderBtn = document.getElementById('viewOrderBtn');
        if (viewOrderBtn) {
            viewOrderBtn.addEventListener('click', () => {
                alert('Order details page would open here. Order ID: ' + (order.orderNumber || order._id));
            });
        }
    }

    showMessage(message, type) {
        // Use auth's showMessage if available
        if (typeof auth !== 'undefined' && auth.showMessage) {
            auth.showMessage(message, type);
        } else {
            // Basic notification fallback
            const messageDiv = document.createElement('div');
            messageDiv.style.cssText = `
                position: fixed;
                top: 100px;
                right: 20px;
                padding: 15px 25px;
                border-radius: 8px;
                font-weight: 600;
                z-index: 10000;
                background: ${type === 'success' ? '#10b981' : '#ef4444'};
                color: white;
                box-shadow: 0 5px 20px rgba(0,0,0,0.2);
            `;
            messageDiv.textContent = message;
            document.body.appendChild(messageDiv);
            setTimeout(() => messageDiv.remove(), 3000);
        }
    }
}

const cartManager = new CartManager();

// Initialize cart when DOM is loaded
if (document.querySelector('.cart-section')) {
    document.addEventListener('DOMContentLoaded', function() {
        cartManager.init();
    });
}

// Make cartManager globally available
window.cartManager = cartManager;