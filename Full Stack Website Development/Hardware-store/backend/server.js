const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const path = require('path');
const bcrypt = require('bcryptjs');
require('dotenv').config();

const app = express();

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, '../frontend')));

// Serve static files from frontend
app.use(express.static(path.join(__dirname, '../frontend')));

// API health check
app.get('/api', (req, res) => {
    res.json({ 
        message: 'Hardware Store API is running!',
        version: '1.0.0',
        endpoints: {
            auth: '/api/auth',
            products: '/api/products', 
            cart: '/api/cart',
            orders: '/api/orders',
            contact: '/api/contact'
        }
    });
});

// Import routes
const authRoutes = require('./routes/auth');
const productRoutes = require('./routes/products');
const cartRoutes = require('./routes/cart');
const orderRoutes = require('./routes/orders');

app.use('/api/auth', authRoutes);
app.use('/api/products', productRoutes);
app.use('/api/cart', cartRoutes);
app.use('/api/orders', orderRoutes);

// Contact messages storage (in production, use database)
let contactMessages = [
    {
        id: '1',
        name: 'Rahul Kumar',
        email: 'rahul@example.com',
        subject: 'Product Inquiry',
        message: 'Do you have cordless drills in stock? I need one for a construction project.',
        status: 'read',
        date: new Date().toISOString(),
        timestamp: new Date().getTime()
    },
    {
        id: '2',
        name: 'Priya Sharma',
        email: 'priya@example.com',
        subject: 'Store Hours',
        message: 'Are you open on Sundays? I want to visit your store.',
        status: 'unread',
        date: new Date(Date.now() - 86400000).toISOString(),
        timestamp: new Date().getTime() - 86400000
    }
];

// Contact route
app.post('/api/contact', (req, res) => {
    try {
        const { name, email, subject, message } = req.body;
        
        // Validate required fields
        if (!name || !email || !subject || !message) {
            return res.status(400).json({ 
                success: false,
                message: 'All fields are required: name, email, subject, message' 
            });
        }

        // Validate email format
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            return res.status(400).json({
                success: false,
                message: 'Please enter a valid email address'
            });
        }

        // Create message object
        const contactMessage = {
            id: Date.now().toString(),
            name,
            email,
            subject,
            message,
            status: 'unread',
            date: new Date().toISOString(),
            timestamp: new Date().getTime()
        };

        // Store message
        contactMessages.unshift(contactMessage);
        
        // Keep only last 100 messages
        if (contactMessages.length > 100) {
            contactMessages = contactMessages.slice(0, 100);
        }

        console.log('📧 Contact Form Submission:', {
            name,
            email,
            subject,
            timestamp: new Date().toISOString()
        });

        res.status(200).json({ 
            success: true,
            message: 'Thank you for your message! We will get back to you soon.',
            messageId: contactMessage.id,
            data: {
                id: contactMessage.id,
                name,
                email,
                subject,
                status: 'unread',
                date: contactMessage.date
            }
        });

    } catch (error) {
        console.error('Error processing contact form:', error);
        res.status(500).json({ 
            success: false,
            message: 'Error processing your message. Please try again later.'
        });
    }
});

// Get contact messages
app.get('/api/contact/messages', (req, res) => {
    try {
        // In production, add authentication middleware here
        const { status, search } = req.query;
        
        let filteredMessages = [...contactMessages];
        
        // Filter by status if provided
        if (status && status !== 'all') {
            filteredMessages = filteredMessages.filter(msg => msg.status === status);
        }
        
        // Search if provided
        if (search) {
            const searchTerm = search.toLowerCase();
            filteredMessages = filteredMessages.filter(msg =>
                msg.name.toLowerCase().includes(searchTerm) ||
                msg.email.toLowerCase().includes(searchTerm) ||
                msg.subject.toLowerCase().includes(searchTerm) ||
                msg.message.toLowerCase().includes(searchTerm)
            );
        }
        
        // Sort by timestamp (newest first)
        filteredMessages.sort((a, b) => b.timestamp - a.timestamp);

        res.status(200).json({
            success: true,
            messages: filteredMessages,
            total: filteredMessages.length,
            totalUnread: contactMessages.filter(msg => msg.status === 'unread').length
        });
    } catch (error) {
        console.error('Error fetching contact messages:', error);
        res.status(500).json({ 
            success: false,
            message: 'Error fetching messages'
        });
    }
});

// Get single contact message
app.get('/api/contact/messages/:id', (req, res) => {
    try {
        const { id } = req.params;
        const message = contactMessages.find(msg => msg.id === id);
        
        if (!message) {
            return res.status(404).json({ 
                success: false,
                message: 'Message not found'
            });
        }
        
        res.status(200).json({
            success: true,
            message: message
        });
    } catch (error) {
        console.error('Error fetching contact message:', error);
        res.status(500).json({ 
            success: false,
            message: 'Error fetching message'
        });
    }
});

// Update message status
app.put('/api/contact/messages/:id', (req, res) => {
    try {
        const { id } = req.params;
        const { status } = req.body;
        
        if (!status || !['read', 'unread', 'replied'].includes(status)) {
            return res.status(400).json({ 
                success: false,
                message: 'Invalid status. Must be: read, unread, or replied'
            });
        }
        
        const messageIndex = contactMessages.findIndex(msg => msg.id === id);
        
        if (messageIndex === -1) {
            return res.status(404).json({ 
                success: false,
                message: 'Message not found'
            });
        }
        
        contactMessages[messageIndex].status = status;
        
        res.status(200).json({
            success: true,
            message: 'Message status updated successfully',
            data: contactMessages[messageIndex]
        });
    } catch (error) {
        console.error('Error updating message status:', error);
        res.status(500).json({ 
            success: false,
            message: 'Error updating message status'
        });
    }
});

// Delete contact message
app.delete('/api/contact/messages/:id', (req, res) => {
    try {
        const { id } = req.params;
        
        const initialLength = contactMessages.length;
        contactMessages = contactMessages.filter(msg => msg.id !== id);
        
        if (contactMessages.length === initialLength) {
            return res.status(404).json({ 
                success: false,
                message: 'Message not found'
            });
        }
        
        res.status(200).json({
            success: true,
            message: 'Message deleted successfully',
            deletedId: id
        });
    } catch (error) {
        console.error('Error deleting contact message:', error);
        res.status(500).json({ 
            success: false,
            message: 'Error deleting message'
        });
    }
});

// Serve frontend routes
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/index.html'));
});

app.get('/admin', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/admin.html'));
});

app.get('/cart', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/cart.html'));
});

// Catch-all route for frontend (for React Router or similar)
app.get('*', (req, res) => {
    if (req.path.startsWith('/api/')) {
        return res.status(404).json({
            success: false,
            message: 'API endpoint not found'
        });
    }
    res.sendFile(path.join(__dirname, '../frontend/index.html'));
});

// Database connection with better error handling
const connectDB = async () => {
    try {
        const conn = await mongoose.connect(process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017/hardwarestore', {
            useNewUrlParser: true,
            useUnifiedTopology: true,
        });
        console.log(`✅ MongoDB connected: ${conn.connection.host}`);
    } catch (error) {
        console.log('❌ MongoDB connection error:', error.message);
        console.log('💡 Make sure MongoDB is running on your system');
        console.log('💡 Command to start MongoDB: mongod');
        process.exit(1);
    }
};

// Create default admin user on startup
async function createDefaultAdmin() {
    try {
        const User = require('./models/User');
        
        // Check if admin already exists
        const adminExists = await User.findOne({ email: 'admin@hardware.com' });
        
        if (!adminExists) {
            const adminUser = new User({
                username: 'admin',
                email: 'admin@hardware.com',
                password: 'admin123',
                role: 'admin',
                phone: '+91 9507256408',
                address: {
                    street: 'Madhuban Road',
                    city: 'Pakridayal',
                    state: 'Bihar',
                    zipCode: '845429',
                    country: 'India'
                }
            });
            
            await adminUser.save();
            console.log('✅ Default admin user created');
            console.log('📧 Email: admin@hardware.com');
            console.log('🔑 Password: admin123');
        } else {
            console.log('✅ Admin user already exists');
        }
        
        // Create a demo customer user
        const demoUserExists = await User.findOne({ email: 'customer@example.com' });
        if (!demoUserExists) {
            const demoUser = new User({
                username: 'demo_customer',
                email: 'customer@example.com',
                password: 'customer123',
                role: 'user',
                phone: '+91 9876543210',
                address: {
                    street: 'Demo Street',
                    city: 'Demo City',
                    state: 'Demo State',
                    zipCode: '123456',
                    country: 'India'
                }
            });
            
            await demoUser.save();
            console.log('✅ Demo customer user created');
            console.log('📧 Email: customer@example.com');
            console.log('🔑 Password: customer123');
        }
    } catch (error) {
        console.log('⚠️ Could not create default users:', error.message);
    }
}

// Error handling middleware
app.use((err, req, res, next) => {
    console.error('Server error:', err.stack);
    res.status(500).json({
        success: false,
        message: 'Something went wrong!',
        error: process.env.NODE_ENV === 'development' ? err.message : undefined
    });
});

// Start server
const startServer = async () => {
    try {
        // Connect to database
        await connectDB();
        
        // Create default users
        await createDefaultAdmin();
        
        const PORT = process.env.PORT || 3000;
        const server = app.listen(PORT, () => {
            console.log(`🚀 Server running on port ${PORT}`);
            console.log(`🌐 Frontend: http://localhost:${PORT}`);
            console.log(`🔗 API: http://localhost:${PORT}/api`);
            console.log(`👑 Admin: http://localhost:${PORT}/admin`);
            console.log(`🛒 Cart: http://localhost:${PORT}/cart`);
            console.log(`📧 Contact API: http://localhost:${PORT}/api/contact`);
            console.log(`📨 Messages API: http://localhost:${PORT}/api/contact/messages`);
            console.log('\n=== Demo Credentials ===');
            console.log('👑 Admin: admin@hardware.com / admin123');
            console.log('👤 Customer: customer@example.com / customer123');
        });
        
        // Handle graceful shutdown
        process.on('SIGTERM', () => {
            console.log('SIGTERM received. Shutting down gracefully...');
            server.close(() => {
                console.log('Server closed');
                mongoose.connection.close(false, () => {
                    console.log('MongoDB connection closed');
                    process.exit(0);
                });
            });
        });
        
    } catch (error) {
        console.error('Failed to start server:', error);
        process.exit(1);
    }
};

// Start the application
startServer();

// Export for testing
module.exports = app;