class AdminManager {
    constructor() {
        this.products = [];
        this.categories = [];
        this.orders = [];
        this.customers = [];
        this.isAuthenticated = false;
        this.currentTab = 'dashboard';
    }

    init() {
        this.checkAuth();
        this.setupEventListeners();
        this.loadDefaultCategories();
    }

    checkAuth() {
        const adminAuth = localStorage.getItem('adminAuth');
        if (adminAuth === 'true') {
            this.isAuthenticated = true;
            this.showAdminPanel();
        } else {
            this.showLoginScreen();
        }
    }

    showLoginScreen() {
        const loginScreen = document.getElementById('adminLoginScreen');
        const adminPanel = document.getElementById('adminPanel');
        
        if (loginScreen) loginScreen.style.display = 'flex';
        if (adminPanel) adminPanel.style.display = 'none';
    }

    showAdminPanel() {
        const loginScreen = document.getElementById('adminLoginScreen');
        const adminPanel = document.getElementById('adminPanel');
        
        if (loginScreen) loginScreen.style.display = 'none';
        if (adminPanel) adminPanel.style.display = 'block';
        
        this.loadDashboardData();
    }

    setupEventListeners() {
        // Admin login
        const adminLoginForm = document.getElementById('adminLoginForm');
        if (adminLoginForm) {
            adminLoginForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleLogin();
            });
        }

        // Admin logout
        const adminLogoutBtn = document.getElementById('adminLogoutBtn');
        if (adminLogoutBtn) {
            adminLogoutBtn.addEventListener('click', () => {
                this.logout();
            });
        }

        // Mobile menu toggle
        const adminMobileToggle = document.getElementById('adminMobileToggle');
        if (adminMobileToggle) {
            adminMobileToggle.addEventListener('click', () => {
                this.toggleMobileMenu();
            });
        }

        const adminSidebarOverlay = document.getElementById('adminSidebarOverlay');
        if (adminSidebarOverlay) {
            adminSidebarOverlay.addEventListener('click', () => {
                this.closeMobileMenu();
            });
        }

        // Tab navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const tab = item.getAttribute('data-tab');
                this.showTab(tab);
                this.closeMobileMenu();
            });
        });

        // Add product button
        const addProductBtn = document.getElementById('addProductBtn');
        if (addProductBtn) {
            addProductBtn.addEventListener('click', () => {
                this.openProductModal();
            });
        }

        // Add category button
        const addCategoryBtn = document.getElementById('addCategoryBtn');
        if (addCategoryBtn) {
            addCategoryBtn.addEventListener('click', () => {
                this.openCategoryModal();
            });
        }

        // Product form submission
        const productForm = document.getElementById('productForm');
        if (productForm) {
            productForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleProductSubmit(e);
            });
        }

        // Category form submission
        const categoryForm = document.getElementById('categoryForm');
        if (categoryForm) {
            categoryForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleCategorySubmit(e);
            });
        }

        // Close modals
        document.querySelectorAll('.close').forEach(closeBtn => {
            closeBtn.addEventListener('click', () => {
                const modal = closeBtn.closest('.modal');
                if (modal) {
                    modal.style.display = 'none';
                }
            });
        });

        // Search products
        const productSearch = document.getElementById('productSearch');
        if (productSearch) {
            productSearch.addEventListener('input', (e) => {
                this.searchProducts(e.target.value);
            });
        }

        // Filter by category
        const categoryFilter = document.getElementById('categoryFilter');
        if (categoryFilter) {
            categoryFilter.addEventListener('change', (e) => {
                this.filterByCategory(e.target.value);
            });
        }

        // Search categories
        const categorySearch = document.getElementById('categorySearch');
        if (categorySearch) {
            categorySearch.addEventListener('input', (e) => {
                this.searchCategories(e.target.value);
            });
        }

        // Search featured products
        const featuredSearch = document.getElementById('featuredSearch');
        if (featuredSearch) {
            featuredSearch.addEventListener('input', (e) => {
                this.searchFeaturedProducts(e.target.value);
            });
        }

        // Search hot deals
        const hotDealsSearch = document.getElementById('hotDealsSearch');
        if (hotDealsSearch) {
            hotDealsSearch.addEventListener('input', (e) => {
                this.searchHotDeals(e.target.value);
            });
        }

        // Search contact messages
        const contactSearch = document.getElementById('contactSearch');
        if (contactSearch) {
            contactSearch.addEventListener('input', (e) => {
                this.searchContactMessages(e.target.value);
            });
        }

        // Filter contact messages by status
        const contactStatusFilter = document.getElementById('contactStatusFilter');
        if (contactStatusFilter) {
            contactStatusFilter.addEventListener('change', (e) => {
                this.filterContactMessages(e.target.value);
            });
        }

        // Click outside modal to close
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.style.display = 'none';
                }
            });
        });
    }

    async handleLogin() {
        const email = document.getElementById('adminEmail');
        const password = document.getElementById('adminPassword');

        if (!email || !password) return;

        const emailValue = email.value;
        const passwordValue = password.value;

        try {
            const response = await fetch('http://localhost:3000/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email: emailValue, password: passwordValue })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.user.role === 'admin') {
                    localStorage.setItem('adminAuth', 'true');
                    localStorage.setItem('token', data.token);
                    this.isAuthenticated = true;
                    this.showAdminPanel();
                    this.showMessage('Login successful!', 'success');
                } else {
                    this.showMessage('Admin access required', 'error');
                }
            } else {
                // Fallback to demo credentials if backend fails
                if (emailValue === 'admin@hardware.com' && passwordValue === 'admin123') {
                    localStorage.setItem('adminAuth', 'true');
                    this.isAuthenticated = true;
                    this.showAdminPanel();
                    this.showMessage('Login successful!', 'success');
                } else {
                    this.showMessage('Invalid credentials!', 'error');
                }
            }
        } catch (error) {
            // Fallback to demo credentials if backend is not available
            if (emailValue === 'admin@hardware.com' && passwordValue === 'admin123') {
                localStorage.setItem('adminAuth', 'true');
                this.isAuthenticated = true;
                this.showAdminPanel();
                this.showMessage('Login successful!', 'success');
            } else {
                this.showMessage('Login failed: ' + error.message, 'error');
            }
        }
    }

    logout() {
        localStorage.removeItem('adminAuth');
        localStorage.removeItem('token');
        this.isAuthenticated = false;
        this.showLoginScreen();
        this.showMessage('Logged out successfully', 'success');
        
        // Redirect to admin login after logout
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }

    toggleMobileMenu() {
        const sidebar = document.getElementById('adminSidebar');
        const overlay = document.getElementById('adminSidebarOverlay');
        if (sidebar) sidebar.classList.toggle('active');
        if (overlay) overlay.classList.toggle('active');
    }

    closeMobileMenu() {
        const sidebar = document.getElementById('adminSidebar');
        const overlay = document.getElementById('adminSidebarOverlay');
        if (sidebar) sidebar.classList.remove('active');
        if (overlay) overlay.classList.remove('active');
    }

    showTab(tabName) {
        // Hide all tabs
        document.querySelectorAll('.admin-tab').forEach(tab => {
            tab.classList.remove('active');
        });

        // Remove active class from nav items
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });

        // Show selected tab
        const tabElement = document.getElementById(tabName);
        if (tabElement) {
            tabElement.classList.add('active');
        }

        // Activate nav item
        const navItem = document.querySelector(`[data-tab="${tabName}"]`);
        if (navItem) {
            navItem.classList.add('active');
        }

        this.currentTab = tabName;

        // Load tab data
        switch (tabName) {
            case 'products':
                this.loadProducts();
                break;
            case 'categories':
                this.loadCategories();
                break;
            case 'featured':
                this.loadFeaturedProducts();
                break;
            case 'hot-deals':
                this.loadHotDeals();
                break;
            case 'orders':
                this.loadOrders();
                break;
            case 'customers':
                this.loadCustomers();
                break;
            case 'contact-messages':
                this.loadContactMessages();
                break;
        }
    }

    async loadDashboardData() {
        await Promise.all([
            this.loadProducts(),
            this.loadCategories(),
            this.loadOrders(),
            this.loadCustomers(),
            this.loadContactMessages()
        ]);
        this.updateStats();
        this.loadRecentOrders();
        this.loadLowStockAlert();
    }

    async loadProducts() {
        try {
            const token = localStorage.getItem('token');
            const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
            
            const response = await fetch('http://localhost:3000/api/products', { headers });
            if (response.ok) {
                const data = await response.json();
                this.products = data.products || data || [];
                this.renderProductsTable();
            } else {
                // Fallback to localStorage if API fails
                const savedProducts = localStorage.getItem('hardwareStoreProducts');
                this.products = savedProducts ? JSON.parse(savedProducts) : [];
                this.renderProductsTable();
            }
        } catch (error) {
            console.error('Error loading products:', error);
            // Fallback to localStorage
            const savedProducts = localStorage.getItem('hardwareStoreProducts');
            this.products = savedProducts ? JSON.parse(savedProducts) : [];
            this.renderProductsTable();
        }
    }

    renderProductsTable() {
        const tbody = document.getElementById('productsTableBody');
        if (!tbody) return;
        
        if (this.products.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center no-data">No products found</td></tr>';
            return;
        }

        tbody.innerHTML = this.products.map(product => `
            <tr>
                <td>
                    <div class="product-table-image">
                        <img src="${product.image || 'https://images.unsplash.com/photo-1581094794329-c8112a89af12?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'}" 
                             alt="${product.name}" onerror="this.src='https://images.unsplash.com/photo-1581094794329-c8112a89af12?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'">
                    </div>
                </td>
                <td>${product.name}</td>
                <td>${product.category}</td>
                <td>₹${(product.price || 0).toFixed(2)}</td>
                <td>
                    <span class="status-badge ${(product.stock || 0) > 10 ? 'status-active' : (product.stock || 0) > 0 ? 'status-low' : 'status-inactive'}">
                        ${product.stock || 0}
                    </span>
                </td>
                <td>
                    <span class="status-badge ${product.featured ? 'status-active' : 'status-inactive'}">
                        ${product.featured ? 'Yes' : 'No'}
                    </span>
                </td>
                <td>
                    <span class="status-badge ${product.onSale ? 'status-active' : 'status-inactive'}">
                        ${product.onSale ? 'Yes' : 'No'}
                    </span>
                </td>
                <td>
                    <div class="table-actions">
                        <button class="btn-table btn-edit" onclick="adminManager.editProduct('${product._id}')">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn-table btn-featured" onclick="adminManager.toggleFeatured('${product._id}')">
                            <i class="fas fa-star"></i>
                        </button>
                        <button class="btn-table btn-hotdeal" onclick="adminManager.toggleHotDeal('${product._id}')">
                            <i class="fas fa-fire"></i>
                        </button>
                        <button class="btn-table btn-delete" onclick="adminManager.deleteProduct('${product._id}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    loadDefaultCategories() {
        // Load default categories if none exist
        const savedCategories = localStorage.getItem('hardwareStoreCategories');
        if (!savedCategories) {
            this.categories = [
                { _id: '1', name: 'Tools', description: 'Hand tools, power tools & accessories', productCount: 0, status: 'active', icon: 'fas fa-hammer' },
                { _id: '2', name: 'Electrical', description: 'Wires, fixtures & electrical supplies', productCount: 0, status: 'active', icon: 'fas fa-bolt' },
                { _id: '3', name: 'Plumbing', description: 'Pipes, fittings & plumbing tools', productCount: 0, status: 'active', icon: 'fas fa-faucet' },
                { _id: '4', name: 'Paint', description: 'Paints, brushes & painting supplies', productCount: 0, status: 'active', icon: 'fas fa-paint-roller' },
                { _id: '5', name: 'Hardware', description: 'Nuts, bolts & fasteners', productCount: 0, status: 'active', icon: 'fas fa-cogs' },
                { _id: '6', name: 'Safety', description: 'Protective gear & safety equipment', productCount: 0, status: 'active', icon: 'fas fa-hard-hat' },
                { _id: '7', name: 'Garden', description: 'Gardening tools and equipment', productCount: 0, status: 'active', icon: 'fas fa-leaf' },
                { _id: '8', name: 'Building Materials', description: 'Construction and building materials', productCount: 0, status: 'active', icon: 'fas fa-home' }
            ];
            this.saveCategories();
        } else {
            this.categories = JSON.parse(savedCategories);
        }
    }

    loadCategories() {
        this.renderCategoriesTable();
    }

    renderCategoriesTable() {
        const tbody = document.getElementById('categoriesTableBody');
        if (!tbody) return;
        
        if (this.categories.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center no-data">No categories found</td></tr>';
            return;
        }

        tbody.innerHTML = this.categories.map(category => `
            <tr>
                <td>
                    <i class="${category.icon || 'fas fa-folder'} fa-2x" style="color: var(--primary);"></i>
                </td>
                <td><strong>${category.name}</strong></td>
                <td>${category.description}</td>
                <td>
                    <span class="status-badge">${this.getProductCountByCategory(category.name)}</span>
                </td>
                <td>
                    <span class="status-badge ${category.status === 'active' ? 'status-active' : 'status-inactive'}">
                        ${category.status}
                    </span>
                </td>
                <td>
                    <div class="table-actions">
                        <button class="btn-table btn-edit" onclick="adminManager.editCategory('${category._id}')">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn-table btn-delete" onclick="adminManager.deleteCategory('${category._id}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    getProductCountByCategory(categoryName) {
        return this.products.filter(product => product.category === categoryName).length;
    }

    loadFeaturedProducts() {
        const featuredProducts = this.products.filter(product => product.featured);
        this.renderFeaturedTable(featuredProducts);
    }

    renderFeaturedTable(products) {
        const tbody = document.getElementById('featuredTableBody');
        if (!tbody) return;
        
        if (products.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center no-data">No featured products found</td></tr>';
            return;
        }

        tbody.innerHTML = products.map(product => `
            <tr>
                <td>
                    <div class="product-table-image">
                        <img src="${product.image || 'https://images.unsplash.com/photo-1581094794329-c8112a89af12?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'}" 
                             alt="${product.name}">
                    </div>
                </td>
                <td>${product.name}</td>
                <td>${product.category}</td>
                <td>₹${(product.price || 0).toFixed(2)}</td>
                <td>${product.stock || 0}</td>
                <td>
                    <span class="status-badge ${product.featured ? 'status-active' : 'status-inactive'}">
                        ${product.featured ? 'Featured' : 'Not Featured'}
                    </span>
                </td>
                <td>
                    <div class="table-actions">
                        <button class="btn-table btn-edit" onclick="adminManager.editProduct('${product._id}')">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn-table btn-delete" onclick="adminManager.toggleFeatured('${product._id}')">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    loadHotDeals() {
        const hotDeals = this.products.filter(product => product.onSale && product.discount > 0);
        this.renderHotDealsTable(hotDeals);
    }

    renderHotDealsTable(products) {
        const tbody = document.getElementById('hotDealsTableBody');
        if (!tbody) return;
        
        if (products.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center no-data">No hot deals found</td></tr>';
            return;
        }

        tbody.innerHTML = products.map(product => {
            const salePrice = product.onSale && product.discount > 0 
                ? product.price * (1 - product.discount / 100)
                : product.price;
            
            return `
                <tr>
                    <td>
                        <div class="product-table-image">
                            <img src="${product.image || 'https://images.unsplash.com/photo-1581094794329-c8112a89af12?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'}" 
                                 alt="${product.name}">
                        </div>
                    </td>
                    <td>${product.name}</td>
                    <td>₹${(product.originalPrice || product.price).toFixed(2)}</td>
                    <td>₹${salePrice.toFixed(2)}</td>
                    <td>${product.discount || 0}%</td>
                    <td>${product.stock || 0}</td>
                    <td>
                        <div class="table-actions">
                            <button class="btn-table btn-edit" onclick="adminManager.editProduct('${product._id}')">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn-table btn-delete" onclick="adminManager.toggleHotDeal('${product._id}')">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    async loadOrders() {
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                throw new Error('No authentication token');
            }

            const response = await fetch('http://localhost:3000/api/orders', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                this.orders = await response.json();
                this.renderOrdersTable();
            } else {
                throw new Error('Failed to fetch orders');
            }
        } catch (error) {
            console.error('Error loading orders:', error);
            this.orders = [];
            this.renderOrdersTable();
            this.showMessage('Error loading orders: ' + error.message, 'error');
        }
    }

    renderOrdersTable() {
        const tbody = document.getElementById('ordersTableBody');
        if (!tbody) return;
        
        if (this.orders.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center no-data">No orders found</td></tr>';
            return;
        }

        tbody.innerHTML = this.orders.map(order => `
            <tr>
                <td>${order.orderNumber || order._id}</td>
                <td>${order.user?.username || order.user?.email || 'Guest'}</td>
                <td>${new Date(order.createdAt || Date.now()).toLocaleDateString()}</td>
                <td>₹${(order.totalAmount || 0).toFixed(2)}</td>
                <td>
                    <span class="status-badge status-${(order.orderStatus || 'pending').toLowerCase()}">
                        ${order.orderStatus || 'Pending'}
                    </span>
                </td>
                <td>
                    <span class="status-badge payment-${(order.paymentStatus || 'pending').toLowerCase()}">
                        ${order.paymentStatus || 'Pending'}
                    </span>
                </td>
                <td>
                    <div class="table-actions">
                        <button class="btn-table btn-view" onclick="adminManager.viewOrder('${order._id}')">
                            <i class="fas fa-eye"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    async loadCustomers() {
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                throw new Error('No authentication token');
            }

            const response = await fetch('http://localhost:3000/api/auth/users', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                this.customers = await response.json();
                this.renderCustomersTable();
            } else {
                throw new Error('Failed to fetch customers');
            }
        } catch (error) {
            console.error('Error loading customers:', error);
            this.customers = [];
            this.renderCustomersTable();
            this.showMessage('Error loading customers: ' + error.message, 'error');
        }
    }

    renderCustomersTable() {
        const tbody = document.getElementById('customersTableBody');
        if (!tbody) return;
        
        if (this.customers.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center no-data">No customers found</td></tr>';
            return;
        }

        tbody.innerHTML = this.customers.map(customer => `
            <tr>
                <td>${customer.username || 'Unknown'}</td>
                <td>${customer.email || 'No email'}</td>
                <td>${customer.phone || 'N/A'}</td>
                <td>${customer.orderCount || 0}</td>
                <td>₹${(customer.totalSpent || 0).toFixed(2)}</td>
                <td>${new Date(customer.createdAt || Date.now()).toLocaleDateString()}</td>
            </tr>
        `).join('');
    }

    async loadContactMessages() {
        try {
            // Try to fetch from backend
            const response = await fetch('http://localhost:3000/api/contact/messages');
            
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.messages) {
                    this.renderContactMessages(data.messages);
                } else {
                    this.renderContactMessages(this.getContactMessages());
                }
            } else {
                // Fallback to localStorage
                this.renderContactMessages(this.getContactMessages());
            }
        } catch (error) {
            console.error('Error loading contact messages:', error);
            this.renderContactMessages(this.getContactMessages());
        }
    }

    getContactMessages() {
        // Get from localStorage
        const savedMessages = localStorage.getItem('hardwareStoreContactMessages');
        if (savedMessages) {
            return JSON.parse(savedMessages);
        }
        
        // Return sample messages for demo
        return [
            {
                id: '1',
                name: 'Rahul Kumar',
                email: 'rahul@example.com',
                subject: 'Product Inquiry',
                message: 'Do you have cordless drills in stock? I need one for a construction project.',
                status: 'read',
                date: new Date().toISOString()
            },
            {
                id: '2',
                name: 'Priya Sharma',
                email: 'priya@example.com',
                subject: 'Store Hours',
                message: 'Are you open on Sundays? I want to visit your store.',
                status: 'unread',
                date: new Date(Date.now() - 86400000).toISOString()
            },
            {
                id: '3',
                name: 'Amit Patel',
                email: 'amit@example.com',
                subject: 'Bulk Order',
                message: 'Can I get a discount for bulk purchase of safety equipment?',
                status: 'unread',
                date: new Date(Date.now() - 172800000).toISOString()
            }
        ];
    }

    renderContactMessages(messages) {
        const tbody = document.getElementById('contactMessagesTableBody');
        if (!tbody) return;

        if (!messages || messages.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center no-data">No contact messages yet</td></tr>';
            return;
        }

        tbody.innerHTML = messages.map(msg => `
            <tr>
                <td>${new Date(msg.date).toLocaleDateString()}</td>
                <td><strong>${msg.name}</strong></td>
                <td>${msg.email}</td>
                <td>${msg.subject}</td>
                <td>
                    <div class="message-preview" title="${msg.message}">
                        ${msg.message.length > 50 ? msg.message.substring(0, 50) + '...' : msg.message}
                    </div>
                </td>
                <td>
                    <span class="status-badge status-${msg.status}">
                        ${msg.status.charAt(0).toUpperCase() + msg.status.slice(1)}
                    </span>
                </td>
                <td>
                    <div class="table-actions">
                        <button class="btn-table btn-view" onclick="adminManager.viewMessage('${msg.id}')" title="View Message">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn-table btn-success" onclick="adminManager.replyToMessage('${msg.email}')" title="Reply">
                            <i class="fas fa-reply"></i>
                        </button>
                        <button class="btn-table btn-delete" onclick="adminManager.deleteMessage('${msg.id}')" title="Delete">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    searchContactMessages(searchTerm) {
        const messages = this.getContactMessages();
        const filteredMessages = messages.filter(msg =>
            msg.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            msg.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
            msg.subject.toLowerCase().includes(searchTerm.toLowerCase()) ||
            msg.message.toLowerCase().includes(searchTerm.toLowerCase())
        );
        
        this.renderContactMessages(filteredMessages);
    }

    filterContactMessages(status) {
        const messages = this.getContactMessages();
        if (!status) {
            this.renderContactMessages(messages);
            return;
        }
        
        const filteredMessages = messages.filter(msg => msg.status === status);
        this.renderContactMessages(filteredMessages);
    }

    viewMessage(messageId) {
        const messages = this.getContactMessages();
        const message = messages.find(msg => msg.id === messageId);
        
        if (message) {
            // Create modal to show full message
            const modalHtml = `
                <div id="messageModal" class="modal" style="display: block;">
                    <div class="modal-content" style="max-width: 600px;">
                        <span class="close" onclick="this.closest('.modal').style.display='none'">&times;</span>
                        <h2>Contact Message</h2>
                        <div class="message-details">
                            <p><strong>From:</strong> ${message.name}</p>
                            <p><strong>Email:</strong> ${message.email}</p>
                            <p><strong>Date:</strong> ${new Date(message.date).toLocaleString()}</p>
                            <p><strong>Subject:</strong> ${message.subject}</p>
                            <div class="message-content">
                                <strong>Message:</strong>
                                <p>${message.message}</p>
                            </div>
                        </div>
                        <div class="modal-actions">
                            <button class="btn btn-primary" onclick="adminManager.replyToMessage('${message.email}')">
                                <i class="fas fa-reply"></i> Reply
                            </button>
                            <button class="btn btn-secondary" onclick="this.closest('.modal').style.display='none'">
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            // Remove existing modal
            const existingModal = document.getElementById('messageModal');
            if (existingModal) existingModal.remove();
            
            // Add new modal
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            // Mark as read
            this.markAsRead(messageId);
        }
    }

    markAsRead(messageId) {
        let messages = this.getContactMessages();
        const messageIndex = messages.findIndex(msg => msg.id === messageId);
        
        if (messageIndex > -1) {
            messages[messageIndex].status = 'read';
            // Save to localStorage
            localStorage.setItem('hardwareStoreContactMessages', JSON.stringify(messages));
            // Reload messages
            this.loadContactMessages();
        }
    }

    replyToMessage(email) {
        window.location.href = `mailto:${email}?subject=Re: Your Inquiry - Rohit Hardware`;
    }

    deleteMessage(messageId) {
        if (confirm('Are you sure you want to delete this message?')) {
            let messages = this.getContactMessages();
            messages = messages.filter(msg => msg.id !== messageId);
            
            // Save to localStorage
            localStorage.setItem('hardwareStoreContactMessages', JSON.stringify(messages));
            
            // Reload messages
            this.loadContactMessages();
            this.showMessage('Message deleted successfully', 'success');
        }
    }

    openProductModal(product = null) {
        const modal = document.getElementById('productModal');
        const title = document.getElementById('modalTitle');
        const form = document.getElementById('productForm');

        if (!modal || !title || !form) return;

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
            document.getElementById('productSku').value = product.sku || '';
            document.getElementById('productImage').value = product.image || '';
            document.getElementById('productFeatured').checked = product.featured || false;
            document.getElementById('productOnSale').checked = product.onSale || false;
        } else {
            title.textContent = 'Add New Product';
            form.reset();
            document.getElementById('productId').value = '';
        }

        modal.style.display = 'block';
    }

    openCategoryModal(category = null) {
        const modal = document.getElementById('categoryModal');
        const title = document.getElementById('categoryModalTitle');
        const form = document.getElementById('categoryForm');

        if (!modal || !title || !form) return;

        if (category) {
            title.textContent = 'Edit Category';
            document.getElementById('categoryId').value = category._id;
            document.getElementById('categoryName').value = category.name;
            document.getElementById('categoryDescription').value = category.description;
            document.getElementById('categoryIcon').value = category.icon || '';
            document.getElementById('categoryStatus').value = category.status || 'active';
        } else {
            title.textContent = 'Add New Category';
            form.reset();
            document.getElementById('categoryId').value = '';
        }

        modal.style.display = 'block';
    }

    closeModal() {
        const modal = document.getElementById('productModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    closeCategoryModal() {
        const modal = document.getElementById('categoryModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    async handleProductSubmit(e) {
        const productId = document.getElementById('productId');
        if (!productId) return;
        
        const productData = {
            name: document.getElementById('productName').value,
            description: document.getElementById('productDescription').value,
            price: parseFloat(document.getElementById('productPrice').value),
            stock: parseInt(document.getElementById('productStock').value),
            category: document.getElementById('productCategory').value,
            discount: parseInt(document.getElementById('productDiscount').value) || 0,
            featured: document.getElementById('productFeatured').checked,
            onSale: document.getElementById('productOnSale').checked
        };

        // Optional fields
        const originalPrice = document.getElementById('productOriginalPrice').value;
        const brand = document.getElementById('productBrand').value;
        const sku = document.getElementById('productSku').value;
        const image = document.getElementById('productImage').value;

        if (originalPrice) productData.originalPrice = parseFloat(originalPrice);
        if (brand) productData.brand = brand;
        if (sku) productData.sku = sku;
        if (image) productData.image = image;

        try {
            const saveBtn = document.getElementById('saveProductBtn');
            saveBtn.disabled = true;
            saveBtn.textContent = 'Saving...';

            const token = localStorage.getItem('token');
            let response;
            if (productId.value) {
                // Update existing product
                response = await fetch(`http://localhost:3000/api/products/${productId.value}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify(productData)
                });
            } else {
                // Create new product
                response = await fetch('http://localhost:3000/api/products', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify(productData)
                });
            }

            if (response.ok) {
                this.showMessage(`Product ${productId.value ? 'updated' : 'created'} successfully!`, 'success');
                this.closeModal();
                await this.loadProducts();
                this.updateStats();
            } else {
                throw new Error('Failed to save product');
            }
        } catch (error) {
            this.showMessage('Error saving product: ' + error.message, 'error');
        } finally {
            const saveBtn = document.getElementById('saveProductBtn');
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = 'Save Product';
            }
        }
    }

    async handleCategorySubmit(e) {
        e.preventDefault();
        
        const categoryId = document.getElementById('categoryId');
        if (!categoryId) return;
        
        const categoryData = {
            name: document.getElementById('categoryName').value,
            description: document.getElementById('categoryDescription').value,
            icon: document.getElementById('categoryIcon').value,
            status: document.getElementById('categoryStatus').value
        };

        try {
            // In a real application, you would send this to your backend
            if (categoryId.value) {
                // Update existing category
                const categoryIndex = this.categories.findIndex(cat => cat._id === categoryId.value);
                if (categoryIndex > -1) {
                    this.categories[categoryIndex] = { ...this.categories[categoryIndex], ...categoryData };
                }
            } else {
                // Create new category
                const newCategory = {
                    _id: Date.now().toString(),
                    ...categoryData,
                    productCount: 0
                };
                this.categories.push(newCategory);
            }

            this.saveCategories();
            this.showMessage(`Category ${categoryId.value ? 'updated' : 'created'} successfully!`, 'success');
            this.closeCategoryModal();
            this.renderCategoriesTable();
        } catch (error) {
            this.showMessage('Error saving category: ' + error.message, 'error');
        }
    }

    saveCategories() {
        localStorage.setItem('hardwareStoreCategories', JSON.stringify(this.categories));
    }

    async editProduct(productId) {
        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`http://localhost:3000/api/products/${productId}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                const product = await response.json();
                this.openProductModal(product);
            } else {
                throw new Error('Product not found');
            }
        } catch (error) {
            this.showMessage('Error loading product: ' + error.message, 'error');
        }
    }

    editCategory(categoryId) {
        const category = this.categories.find(cat => cat._id === categoryId);
        if (category) {
            this.openCategoryModal(category);
        } else {
            this.showMessage('Category not found', 'error');
        }
    }

    async toggleFeatured(productId) {
        try {
            const product = this.products.find(p => p._id === productId);
            if (!product) {
                throw new Error('Product not found');
            }

            const updatedProduct = {
                ...product,
                featured: !product.featured
            };

            const token = localStorage.getItem('token');
            const response = await fetch(`http://localhost:3000/api/products/${productId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(updatedProduct)
            });

            if (response.ok) {
                product.featured = !product.featured;
                this.showMessage(`Product ${product.featured ? 'added to' : 'removed from'} featured!`, 'success');
                this.renderProductsTable();
                this.loadFeaturedProducts();
            } else {
                throw new Error('Failed to update product');
            }
        } catch (error) {
            this.showMessage('Error updating featured status: ' + error.message, 'error');
        }
    }

    async toggleHotDeal(productId) {
        try {
            const product = this.products.find(p => p._id === productId);
            if (!product) {
                throw new Error('Product not found');
            }

            const updatedProduct = {
                ...product,
                onSale: !product.onSale
            };

            // If turning on sale and no discount set, add default discount
            if (updatedProduct.onSale && !updatedProduct.discount) {
                updatedProduct.discount = 20;
            }

            const token = localStorage.getItem('token');
            const response = await fetch(`http://localhost:3000/api/products/${productId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(updatedProduct)
            });

            if (response.ok) {
                product.onSale = !product.onSale;
                if (product.onSale && !product.discount) {
                    product.discount = 20;
                }
                this.showMessage(`Product ${product.onSale ? 'added to' : 'removed from'} hot deals!`, 'success');
                this.renderProductsTable();
                this.loadHotDeals();
            } else {
                throw new Error('Failed to update product');
            }
        } catch (error) {
            this.showMessage('Error updating hot deal status: ' + error.message, 'error');
        }
    }

    async deleteProduct(productId) {
        if (!confirm('Are you sure you want to delete this product?')) {
            return;
        }

        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`http://localhost:3000/api/products/${productId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                this.showMessage('Product deleted successfully!', 'success');
                await this.loadProducts();
                await this.loadHotDeals();
                this.updateStats();
            } else {
                throw new Error('Failed to delete product');
            }
        } catch (error) {
            this.showMessage('Error deleting product: ' + error.message, 'error');
        }
    }

    deleteCategory(categoryId) {
        if (!confirm('Are you sure you want to delete this category?')) {
            return;
        }

        try {
            this.categories = this.categories.filter(cat => cat._id !== categoryId);
            this.saveCategories();
            this.showMessage('Category deleted successfully!', 'success');
            this.renderCategoriesTable();
        } catch (error) {
            this.showMessage('Error deleting category: ' + error.message, 'error');
        }
    }

    searchProducts(searchTerm) {
        const filteredProducts = this.products.filter(product =>
            product.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            product.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
            product.description.toLowerCase().includes(searchTerm.toLowerCase())
        );
        
        this.renderFilteredProducts(filteredProducts);
    }

    filterByCategory(category) {
        if (!category) {
            this.renderProductsTable();
            return;
        }

        const filteredProducts = this.products.filter(product =>
            product.category === category
        );
        
        this.renderFilteredProducts(filteredProducts);
    }

    renderFilteredProducts(products) {
        const tbody = document.getElementById('productsTableBody');
        if (!tbody) return;
        
        if (products.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center no-data">No products found</td></tr>';
            return;
        }

        tbody.innerHTML = products.map(product => `
            <tr>
                <td>
                    <div class="product-table-image">
                        <img src="${product.image || 'https://images.unsplash.com/photo-1581094794329-c8112a89af12?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'}" 
                             alt="${product.name}">
                    </div>
                </td>
                <td>${product.name}</td>
                <td>${product.category}</td>
                <td>₹${product.price.toFixed(2)}</td>
                <td>${product.stock}</td>
                <td>
                    <span class="status-badge ${product.featured ? 'status-active' : 'status-inactive'}">
                        ${product.featured ? 'Yes' : 'No'}
                    </span>
                </td>
                <td>
                    <span class="status-badge ${product.onSale ? 'status-active' : 'status-inactive'}">
                        ${product.onSale ? 'Yes' : 'No'}
                    </span>
                </td>
                <td>
                    <div class="table-actions">
                        <button class="btn-table btn-edit" onclick="adminManager.editProduct('${product._id}')">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn-table btn-featured" onclick="adminManager.toggleFeatured('${product._id}')">
                            <i class="fas fa-star"></i>
                        </button>
                        <button class="btn-table btn-hotdeal" onclick="adminManager.toggleHotDeal('${product._id}')">
                            <i class="fas fa-fire"></i>
                        </button>
                        <button class="btn-table btn-delete" onclick="adminManager.deleteProduct('${product._id}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    searchCategories(searchTerm) {
        const filteredCategories = this.categories.filter(category =>
            category.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            category.description.toLowerCase().includes(searchTerm.toLowerCase())
        );
        
        this.renderFilteredCategories(filteredCategories);
    }

    searchFeaturedProducts(searchTerm) {
        const featuredProducts = this.products.filter(product => 
            product.featured && (
                product.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                product.category.toLowerCase().includes(searchTerm.toLowerCase())
            )
        );
        this.renderFeaturedTable(featuredProducts);
    }

    searchHotDeals(searchTerm) {
        const hotDeals = this.products.filter(product => 
            product.onSale && (
                product.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                product.category.toLowerCase().includes(searchTerm.toLowerCase())
            )
        );
        this.renderHotDealsTable(hotDeals);
    }

    renderFilteredCategories(categories) {
        const tbody = document.getElementById('categoriesTableBody');
        if (!tbody) return;
        
        if (categories.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center no-data">No categories found</td></tr>';
            return;
        }

        tbody.innerHTML = categories.map(category => `
            <tr>
                <td>
                    <i class="${category.icon || 'fas fa-folder'} fa-2x" style="color: var(--primary);"></i>
                </td>
                <td><strong>${category.name}</strong></td>
                <td>${category.description}</td>
                <td>${this.getProductCountByCategory(category.name)}</td>
                <td>
                    <span class="status-badge ${category.status === 'active' ? 'status-active' : 'status-inactive'}">
                        ${category.status}
                    </span>
                </td>
                <td>
                    <div class="table-actions">
                        <button class="btn-table btn-edit" onclick="adminManager.editCategory('${category._id}')">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn-table btn-delete" onclick="adminManager.deleteCategory('${category._id}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    updateStats() {
        const totalProducts = document.getElementById('totalProducts');
        const totalOrders = document.getElementById('totalOrders');
        const totalCustomers = document.getElementById('totalCustomers');
        const totalRevenue = document.getElementById('totalRevenue');
        
        if (totalProducts) totalProducts.textContent = this.products.length;
        if (totalOrders) totalOrders.textContent = this.orders.length;
        if (totalCustomers) totalCustomers.textContent = this.customers.length;
        
        // Calculate total revenue
        const revenue = this.orders.reduce((sum, order) => sum + (order.totalAmount || 0), 0);
        if (totalRevenue) totalRevenue.textContent = `₹${revenue.toFixed(2)}`;
    }

    loadRecentOrders() {
        const recentOrders = this.orders.slice(0, 5);
        const container = document.getElementById('recentOrders');
        if (!container) return;
        
        if (recentOrders.length === 0) {
            container.innerHTML = '<div class="activity-item"><div class="activity-info"><h4>No orders yet</h4><p>Orders will appear here</p></div></div>';
            return;
        }

        container.innerHTML = recentOrders.map(order => `
            <div class="activity-item">
                <div class="activity-info">
                    <h4>Order #${order.orderNumber || order._id}</h4>
                    <p>${order.user?.username || 'Customer'} - ${new Date(order.createdAt || Date.now()).toLocaleDateString()}</p>
                </div>
                <div class="activity-amount">₹${(order.totalAmount || 0).toFixed(2)}</div>
            </div>
        `).join('');
    }

    loadLowStockAlert() {
        const lowStockProducts = this.products.filter(product => (product.stock || 0) < 10 && (product.stock || 0) > 0);
        const container = document.getElementById('lowStockAlert');
        if (!container) return;
        
        if (lowStockProducts.length === 0) {
            container.innerHTML = '<div class="activity-item"><div class="activity-info"><h4>No low stock items</h4><p>All products are well stocked</p></div></div>';
            return;
        }

        container.innerHTML = lowStockProducts.map(product => `
            <div class="activity-item">
                <div class="activity-info">
                    <h4>${product.name}</h4>
                    <p>Only ${product.stock} left in stock</p>
                </div>
                <div class="activity-amount" style="color: var(--warning);">Low Stock</div>
            </div>
        `).join('');
    }

    viewOrder(orderId) {
        // Implement order details view
        this.showMessage('Order details view would open here', 'info');
    }

    showMessage(message, type) {
        // Create message element
        const messageDiv = document.createElement('div');
        messageDiv.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 8px;
            font-weight: 600;
            z-index: 10000;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
            max-width: 400px;
            word-wrap: break-word;
        `;
        messageDiv.textContent = message;

        document.body.appendChild(messageDiv);

        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.remove();
            }
        }, 5000);
    }
}

// Initialize admin manager
document.addEventListener('DOMContentLoaded', function() {
    window.adminManager = new AdminManager();
    adminManager.init();
});

// Make adminManager globally available
window.adminManager = adminManager;