class ProductManager {
    constructor() {
        this.products = [];
        this.currentProduct = null;
        this.filters = {
            category: '',
            search: '',
            minPrice: '',
            maxPrice: '',
            sortBy: 'createdAt',
            sortOrder: 'desc'
        };
    }

    async loadFeaturedProducts() {
        try {
            // First try to get from API
            let products = [];
            try {
                products = await api.getFeaturedProducts();
            } catch (error) {
                console.log('API not available, using local products for featured');
                // Fallback to local products marked as featured
                const allProducts = await this.getAllProducts();
                products = allProducts.filter(product => product.featured).slice(0, 8);
            }
            this.renderProducts(products, 'featuredProducts');
        } catch (error) {
            console.error('Error loading featured products:', error);
            this.showMessage('Error loading featured products', 'error');
        }
    }

    async loadSaleProducts() {
        try {
            // First try to get from API
            let products = [];
            try {
                products = await api.getSaleProducts();
            } catch (error) {
                console.log('API not available, using local products for sale');
                // Fallback to local products marked as onSale
                const allProducts = await this.getAllProducts();
                products = allProducts.filter(product => product.onSale && product.discount > 0).slice(0, 8);
            }
            this.renderProducts(products, 'saleProducts');
        } catch (error) {
            console.error('Error loading sale products:', error);
            this.showMessage('Error loading sale products', 'error');
        }
    }

    async getAllProducts() {
        try {
            // Try API first
            const response = await api.getProducts();
            return response.products || response || [];
        } catch (error) {
            console.log('API not available, using local storage products');
            // Fallback to localStorage
            const savedProducts = localStorage.getItem('hardwareStoreProducts');
            if (savedProducts) {
                return JSON.parse(savedProducts);
            }
            return [];
        }
    }

    async loadProducts(filters = {}) {
        try {
            const response = await api.getProducts(filters);
            this.products = response.products;
            return response;
        } catch (error) {
            console.log('API not available, using local products');
            const allProducts = await this.getAllProducts();
            
            // Apply filters locally
            let filteredProducts = allProducts;
            
            if (filters.category) {
                filteredProducts = filteredProducts.filter(product => 
                    product.category === filters.category
                );
            }
            
            if (filters.search) {
                const searchTerm = filters.search.toLowerCase();
                filteredProducts = filteredProducts.filter(product =>
                    product.name.toLowerCase().includes(searchTerm) ||
                    product.description.toLowerCase().includes(searchTerm) ||
                    product.category.toLowerCase().includes(searchTerm)
                );
            }
            
            if (filters.featured === 'true') {
                filteredProducts = filteredProducts.filter(product => product.featured);
            }
            
            if (filters.onSale === 'true') {
                filteredProducts = filteredProducts.filter(product => product.onSale && product.discount > 0);
            }

            this.products = filteredProducts;
            return { products: filteredProducts, total: filteredProducts.length };
        }
    }

    async loadProductsByCategory(category) {
    try {
        console.log(`Loading products for category: ${category}`);
        
        let products = [];
        try {
            const response = await api.getProducts({ category: category });
            products = response.products || [];
        } catch (error) {
            console.log('API not available, filtering local products by category');
            const allProducts = await this.getAllProducts();
            products = allProducts.filter(product => 
                product.category && product.category.toLowerCase() === category.toLowerCase()
            );
        }
        
        console.log(`Found ${products.length} products for ${category}`);
        
        // Update the featured products section
        this.renderProducts(products, 'featuredProducts');
        
        // Update section header
        const sectionHeader = document.querySelector('.featured-products .section-header');
        if (sectionHeader) {
            sectionHeader.querySelector('h2').textContent = `${category} Products`;
            sectionHeader.querySelector('p').textContent = `Browse our ${category.toLowerCase()} collection (${products.length} items)`;
        }
        
        // Scroll to products section - with safety check
        setTimeout(() => {
            const featuredSection = document.getElementById('featured');
            if (featuredSection) {
                featuredSection.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'start' 
                });
            }
        }, 100);
        
    } catch (error) {
        console.error('Error loading category products:', error);
        this.showMessage('Error loading category products. Please try again.', 'error');
    }
}

// Also update the setupCategoryNavigation method:
setupCategoryNavigation() {
    // Setup click handlers for category cards
    document.addEventListener('click', (e) => {
        // Handle category cards
        if (e.target.closest('.category-card')) {
            e.preventDefault();
            const card = e.target.closest('.category-card');
            const category = card.getAttribute('data-category');
            if (category) {
                this.loadProductsByCategory(category);
            }
        }
        
        // Handle dropdown category links
        if (e.target.matches('.dropdown-menu a, .sidebar-dropdown-menu a, .footer-section a[data-category]')) {
            e.preventDefault();
            const category = e.target.getAttribute('data-category');
            if (category) {
                this.loadProductsByCategory(category);
                // Close mobile menu if open
                if (typeof closeMobileMenu === 'function') {
                    closeMobileMenu();
                }
            }
        }
    });
}

    renderProducts(products, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (!products || products.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-box-open"></i>
                    <h3>No products found</h3>
                    <p>Try adjusting your search or filters</p>
                </div>
            `;
            return;
        }

        container.innerHTML = products.map(product => this.createProductCard(product)).join('');
    }

    createProductCard(product) {
        const salePrice = product.onSale && product.discount > 0 
            ? product.price * (1 - product.discount / 100)
            : null;

        const isOutOfStock = product.stock === 0;

        return `
            <div class="product-card" data-product-id="${product._id}">
                ${product.featured ? '<div class="product-badge featured">Featured</div>' : ''}
                ${product.onSale ? '<div class="product-badge sale">Sale</div>' : ''}
                ${isOutOfStock ? '<div class="product-badge">Out of Stock</div>' : ''}
                
                <div class="product-image">
                    <img src="${product.image || 'https://images.unsplash.com/photo-1581094794329-c8112a89af12?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'}" 
                         alt="${product.name}" 
                         onerror="this.src='https://images.unsplash.com/photo-1581094794329-c8112a89af12?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'">
                </div>
                
                <div class="product-info">
                    <div class="product-category">${product.category}</div>
                    <h3 class="product-name">${product.name}</h3>
                    <p class="product-description">${product.description}</p>
                    
                    <div class="product-price">
                        <span class="current-price">
                            ₹${salePrice ? salePrice.toFixed(2) : product.price.toFixed(2)}
                        </span>
                        ${salePrice ? `
                            <span class="original-price">₹${product.price.toFixed(2)}</span>
                            <span class="discount">-${product.discount}%</span>
                        ` : ''}
                    </div>
                    
                    <div class="product-meta">
                        <div class="product-stock ${isOutOfStock ? 'stock-out' : 'stock-in'}">
                            <i class="fas ${isOutOfStock ? 'fa-times-circle' : 'fa-check-circle'}"></i>
                            ${isOutOfStock ? 'Out of Stock' : `${product.stock} in stock`}
                        </div>
                        <div class="product-rating">
                            <i class="fas fa-star"></i>
                            <span>${product.rating || '4.5'}</span>
                        </div>
                    </div>
                    
                    <div class="product-actions">
                        <button class="btn-add-cart" 
                                onclick="productManager.addToCart('${product._id}')"
                                ${isOutOfStock ? 'disabled' : ''}>
                            <i class="fas fa-shopping-cart"></i>
                            ${isOutOfStock ? 'Out of Stock' : 'Add to Cart'}
                        </button>
                        <button class="btn-quick-view" onclick="productManager.quickView('${product._id}')">
                            <i class="fas fa-eye"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    async addToCart(productId, quantity = 1) {
        if (!auth.isAuthenticated()) {
            auth.showMessage('Please login to add items to cart', 'error');
            auth.showAuthModal('login');
            return;
        }

        try {
            await api.addToCart(productId, quantity);
            auth.updateCartCount();
            this.showMessage('Product added to cart!', 'success');
        } catch (error) {
            this.showMessage('Failed to add to cart: ' + error.message, 'error');
        }
    }

    async quickView(productId) {
        try {
            let product;
            try {
                product = await api.getProduct(productId);
            } catch (error) {
                console.log('API not available, getting product from local storage');
                const allProducts = await this.getAllProducts();
                product = allProducts.find(p => p._id === productId);
                if (!product) {
                    throw new Error('Product not found');
                }
            }
            this.showQuickView(product);
        } catch (error) {
            this.showMessage('Error loading product details: ' + error.message, 'error');
        }
    }

    showQuickView(product) {
        const modal = document.getElementById('quickViewModal');
        const content = document.getElementById('quickViewContent');
        
        const salePrice = product.onSale && product.discount > 0 
            ? product.price * (1 - product.discount / 100)
            : null;

        content.innerHTML = `
            <div class="quickview-content">
                <div class="quickview-image">
                    <img src="${product.image || 'https://images.unsplash.com/photo-1581094794329-c8112a89af12?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'}" 
                         alt="${product.name}">
                </div>
                <div class="quickview-details">
                    <h2>${product.name}</h2>
                    <div class="product-category">${product.category}</div>
                    <div class="quickview-price">
                        ₹${salePrice ? salePrice.toFixed(2) : product.price.toFixed(2)}
                        ${salePrice ? `
                            <span class="original-price">₹${product.price.toFixed(2)}</span>
                            <span class="discount">-${product.discount}%</span>
                        ` : ''}
                    </div>
                    <p class="quickview-description">${product.description}</p>
                    
                    <div class="quickview-actions">
                        <div class="quantity-selector">
                            <button onclick="productManager.decreaseQuantity()">-</button>
                            <input type="number" id="quickViewQuantity" value="1" min="1" max="${product.stock}">
                            <button onclick="productManager.increaseQuantity(${product.stock})">+</button>
                        </div>
                        <button class="btn btn-primary" onclick="productManager.addToCart('${product._id}', parseInt(document.getElementById('quickViewQuantity').value))">
                            <i class="fas fa-shopping-cart"></i>
                            Add to Cart
                        </button>
                    </div>
                    
                    <div class="product-meta" style="margin-top: 20px;">
                        <div class="product-stock ${product.stock === 0 ? 'stock-out' : 'stock-in'}">
                            <i class="fas ${product.stock === 0 ? 'fa-times-circle' : 'fa-check-circle'}"></i>
                            ${product.stock === 0 ? 'Out of Stock' : `${product.stock} in stock`}
                        </div>
                    </div>
                </div>
            </div>
        `;

        modal.style.display = 'block';
    }

    increaseQuantity(maxStock) {
        const input = document.getElementById('quickViewQuantity');
        let value = parseInt(input.value);
        if (value < maxStock) {
            input.value = value + 1;
        }
    }

    decreaseQuantity() {
        const input = document.getElementById('quickViewQuantity');
        let value = parseInt(input.value);
        if (value > 1) {
            input.value = value - 1;
        }
    }

    closeQuickView() {
        document.getElementById('quickViewModal').style.display = 'none';
    }

    async searchProducts(searchTerm) {
        this.filters.search = searchTerm;
        const response = await this.loadProducts(this.filters);
        this.renderProducts(response.products, 'featuredProducts');
        
        // Update section header for search results
        const sectionHeader = document.querySelector('.featured-products .section-header');
        if (sectionHeader && searchTerm) {
            sectionHeader.querySelector('h2').textContent = `Search Results for "${searchTerm}"`;
            sectionHeader.querySelector('p').textContent = `${response.total} products found`;
        }
        
        // Scroll to featured section
        const featuredSection = document.getElementById('featured');
        if (featuredSection) {
            featuredSection.scrollIntoView({ behavior: 'smooth' });
        }
    }

    // Load categories for main website
    async loadCategoriesForMainSite() {
        try {
            const savedCategories = localStorage.getItem('hardwareStoreCategories');
            if (savedCategories) {
                const categories = JSON.parse(savedCategories);
                // Update categories section in main website
                const categoriesGrid = document.querySelector('.categories-grid');
                if (categoriesGrid) {
                    categoriesGrid.innerHTML = categories
                        .filter(cat => cat.status === 'active')
                        .map(category => `
                            <div class="category-card" data-category="${category.name}">
                                <div class="category-icon">
                                    <i class="${category.icon || 'fas fa-folder'}"></i>
                                </div>
                                <h3>${category.name}</h3>
                                <p>${category.description}</p>
                            </div>
                        `).join('');

                    // Add click event listeners to category cards
                    categoriesGrid.querySelectorAll('.category-card').forEach(card => {
                        card.addEventListener('click', () => {
                            const category = card.getAttribute('data-category');
                            this.loadProductsByCategory(category);
                        });
                    });
                }

                // Update category dropdowns in navigation
                this.updateCategoryDropdowns(categories);
            }
        } catch (error) {
            console.error('Error loading categories for main site:', error);
        }
    }

    updateCategoryDropdowns(categories) {
        // Update desktop dropdown
        const desktopDropdown = document.querySelector('.dropdown-menu');
        if (desktopDropdown) {
            desktopDropdown.innerHTML = categories
                .filter(cat => cat.status === 'active')
                .map(category => `
                    <a href="#" data-category="${category.name}">${category.name}</a>
                `).join('');

            // Add event listeners
            desktopDropdown.querySelectorAll('a').forEach(link => {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    const category = link.getAttribute('data-category');
                    this.loadProductsByCategory(category);
                });
            });
        }

        // Update mobile dropdown
        const mobileDropdown = document.querySelector('.sidebar-dropdown-menu');
        if (mobileDropdown) {
            mobileDropdown.innerHTML = categories
                .filter(cat => cat.status === 'active')
                .map(category => `
                    <li><a href="#" data-category="${category.name}">${category.name}</a></li>
                `).join('');

            // Add event listeners
            mobileDropdown.querySelectorAll('a').forEach(link => {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    const category = link.getAttribute('data-category');
                    this.loadProductsByCategory(category);
                    // Close mobile menu
                    closeMobileMenu();
                });
            });
        }

        // Update footer categories
        const footerCategories = document.querySelector('.footer-section:nth-child(3) ul');
        if (footerCategories) {
            footerCategories.innerHTML = categories
                .filter(cat => cat.status === 'active')
                .slice(0, 5)
                .map(category => `
                    <li><a href="#" data-category="${category.name}">${category.name}</a></li>
                `).join('');

            // Add event listeners
            footerCategories.querySelectorAll('a').forEach(link => {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    const category = link.getAttribute('data-category');
                    this.loadProductsByCategory(category);
                });
            });
        }
    }

    // Initialize main website
    async initMainWebsite() {
        // Load categories first
        await this.loadCategoriesForMainSite();
        
        // Then load featured and sale products
        await this.loadFeaturedProducts();
        await this.loadSaleProducts();

        // Set up category navigation
        this.setupCategoryNavigation();
    }

    setupCategoryNavigation() {
        // Category cards are already set up in loadCategoriesForMainSite
        // Additional navigation setup if needed
        document.addEventListener('click', (e) => {
            if (e.target.matches('.dropdown-menu a, .sidebar-dropdown-menu a, .footer-section a[data-category]')) {
                e.preventDefault();
                const category = e.target.getAttribute('data-category');
                if (category) {
                    this.loadProductsByCategory(category);
                }
            }
        });
    }

    // Admin product management methods
    async createProduct(productData) {
        try {
            // Try API first
            try {
                await api.createProduct(productData);
            } catch (error) {
                console.log('API not available, saving product locally');
                // Save to localStorage
                const allProducts = await this.getAllProducts();
                const newProduct = {
                    _id: Date.now().toString(),
                    ...productData,
                    createdAt: new Date(),
                    rating: 4.5,
                    reviewCount: 0
                };
                allProducts.push(newProduct);
                localStorage.setItem('hardwareStoreProducts', JSON.stringify(allProducts));
            }
            
            this.showMessage('Product created successfully!', 'success');
            
            // Refresh the products in admin panel if available
            if (typeof adminManager !== 'undefined') {
                adminManager.loadProducts();
            }
            
            // Refresh featured and sale products on main site
            await this.loadFeaturedProducts();
            await this.loadSaleProducts();
            
        } catch (error) {
            this.showMessage('Error creating product: ' + error.message, 'error');
        }
    }

    async updateProduct(id, productData) {
        try {
            // Try API first
            try {
                await api.updateProduct(id, productData);
            } catch (error) {
                console.log('API not available, updating product locally');
                // Update in localStorage
                const allProducts = await this.getAllProducts();
                const productIndex = allProducts.findIndex(p => p._id === id);
                if (productIndex > -1) {
                    allProducts[productIndex] = { ...allProducts[productIndex], ...productData };
                    localStorage.setItem('hardwareStoreProducts', JSON.stringify(allProducts));
                }
            }
            
            this.showMessage('Product updated successfully!', 'success');
            
            // Refresh the products in admin panel if available
            if (typeof adminManager !== 'undefined') {
                adminManager.loadProducts();
            }
            
            // Refresh featured and sale products on main site
            await this.loadFeaturedProducts();
            await this.loadSaleProducts();
            
        } catch (error) {
            this.showMessage('Error updating product: ' + error.message, 'error');
        }
    }

    async editProduct(id) {
        try {
            let product;
            try {
                product = await api.getProduct(id);
            } catch (error) {
                console.log('API not available, getting product from local storage');
                const allProducts = await this.getAllProducts();
                product = allProducts.find(p => p._id === id);
                if (!product) {
                    throw new Error('Product not found');
                }
            }
            this.openModal(product);
        } catch (error) {
            this.showMessage('Error loading product: ' + error.message, 'error');
        }
    }

    openModal(product = null) {
        const modal = document.getElementById('productModal');
        const title = document.getElementById('modalTitle');
        const form = document.getElementById('productForm');

        if (product) {
            title.textContent = 'Edit Product';
            document.getElementById('productId').value = product._id;
            document.getElementById('productName').value = product.name;
            document.getElementById('productDescription').value = product.description;
            document.getElementById('productPrice').value = product.price;
            document.getElementById('productOriginalPrice').value = product.originalPrice || '';
            document.getElementById('productCategory').value = product.category;
            document.getElementById('productBrand').value = product.brand || '';
            document.getElementById('productStock').value = product.stock;
            document.getElementById('productDiscount').value = product.discount || 0;
            document.getElementById('productImage').value = product.image || '';
            document.getElementById('productFeatured').checked = product.featured || false;
            document.getElementById('productOnSale').checked = product.onSale || false;
        } else {
            title.textContent = 'Add Product';
            form.reset();
        }

        modal.style.display = 'block';
    }

    closeModal() {
        const modal = document.getElementById('productModal');
        modal.style.display = 'none';
        document.getElementById('productForm').reset();
    }

    handleFormSubmit(event) {
        event.preventDefault();
        
        const formData = {
            name: document.getElementById('productName').value,
            description: document.getElementById('productDescription').value,
            price: parseFloat(document.getElementById('productPrice').value),
            originalPrice: document.getElementById('productOriginalPrice').value ? parseFloat(document.getElementById('productOriginalPrice').value) : undefined,
            category: document.getElementById('productCategory').value,
            brand: document.getElementById('productBrand').value || undefined,
            stock: parseInt(document.getElementById('productStock').value),
            discount: parseInt(document.getElementById('productDiscount').value) || 0,
            image: document.getElementById('productImage').value || undefined,
            featured: document.getElementById('productFeatured').checked,
            onSale: document.getElementById('productOnSale').checked
        };

        const productId = document.getElementById('productId').value;

        if (productId) {
            this.updateProduct(productId, formData);
        } else {
            this.createProduct(formData);
        }
        
        this.closeModal();
    }

    showMessage(message, type) {
        // Use auth's showMessage if available, otherwise create basic notification
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

const productManager = new ProductManager();

// Initialize main website when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    productManager.initMainWebsite();
});