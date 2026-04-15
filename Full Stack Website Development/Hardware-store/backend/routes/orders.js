const express = require('express');
const Order = require('../models/Order');
const Product = require('../models/Product');
const User = require('../models/User');
const { auth, adminAuth } = require('../middleware/auth');

const router = express.Router();

// Create new order
router.post('/', auth, async (req, res) => {
    try {
        const { items, shippingAddress, billingAddress, paymentMethod, notes } = req.body;

        // Calculate total amount and validate items
        let totalAmount = 0;
        const orderItems = [];

        for (const item of items) {
            const product = await Product.findById(item.product);
            if (!product) {
                return res.status(400).json({ message: `Product ${item.product} not found` });
            }

            if (product.stock < item.quantity) {
                return res.status(400).json({ 
                    message: `Insufficient stock for ${product.name}. Available: ${product.stock}` 
                });
            }

            const itemTotal = product.salePrice * item.quantity;
            totalAmount += itemTotal;

            orderItems.push({
                product: product._id,
                quantity: item.quantity,
                price: product.salePrice,
                name: product.name,
                image: product.image
            });

            // Update product stock
            product.stock -= item.quantity;
            await product.save();
        }

        // Add shipping cost and tax (simplified calculation)
        const shippingCost = totalAmount > 500 ? 0 : 50;
        const tax = totalAmount * 0.08; // 8% tax
        totalAmount += shippingCost + tax;

        // Create order
        const order = new Order({
            user: req.user._id,
            items: orderItems,
            totalAmount,
            shippingAddress,
            billingAddress: billingAddress || shippingAddress,
            paymentMethod,
            notes,
            paymentStatus: 'completed', // For demo, assume payment is always successful
            orderStatus: 'confirmed'
        });

        await order.save();

        // Update user's order count and total spent
        await User.findByIdAndUpdate(req.user._id, {
            $inc: { 
                orderCount: 1,
                totalSpent: totalAmount
            }
        });

        // Clear user's cart
        req.user.cart = [];
        await req.user.save();

        res.status(201).json(order);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Get user's orders
router.get('/my-orders', auth, async (req, res) => {
    try {
        const orders = await Order.find({ user: req.user._id })
            .populate('user', 'username email')
            .sort({ createdAt: -1 });

        res.json(orders);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Get all orders (admin only)
router.get('/', adminAuth, async (req, res) => {
    try {
        const orders = await Order.find()
            .populate('user', 'username email phone')
            .sort({ createdAt: -1 });

        res.json(orders);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Get single order
router.get('/:id', auth, async (req, res) => {
    try {
        const order = await Order.findById(req.params.id)
            .populate('user', 'username email phone')
            .populate('items.product');

        if (!order) {
            return res.status(404).json({ message: 'Order not found' });
        }

        // Check if user owns the order or is admin
        if (order.user._id.toString() !== req.user._id.toString() && req.user.role !== 'admin') {
            return res.status(403).json({ message: 'Access denied' });
        }

        res.json(order);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Update order status (admin only)
router.put('/:id/status', adminAuth, async (req, res) => {
    try {
        const { orderStatus } = req.body;

        const order = await Order.findByIdAndUpdate(
            req.params.id,
            { orderStatus },
            { new: true, runValidators: true }
        ).populate('user', 'username email');

        if (!order) {
            return res.status(404).json({ message: 'Order not found' });
        }

        res.json(order);
    } catch (error) {
        res.status(400).json({ message: error.message });
    }
});

// Update payment status (admin only)
router.put('/:id/payment', adminAuth, async (req, res) => {
    try {
        const { paymentStatus } = req.body;

        const order = await Order.findByIdAndUpdate(
            req.params.id,
            { paymentStatus },
            { new: true, runValidators: true }
        ).populate('user', 'username email');

        if (!order) {
            return res.status(404).json({ message: 'Order not found' });
        }

        res.json(order);
    } catch (error) {
        res.status(400).json({ message: error.message });
    }
});

// Get order statistics (admin only)
router.get('/stats/overview', adminAuth, async (req, res) => {
    try {
        const totalOrders = await Order.countDocuments();
        const totalRevenue = await Order.aggregate([
            { $match: { paymentStatus: 'completed' } },
            { $group: { _id: null, total: { $sum: '$totalAmount' } } }
        ]);
        
        const recentOrders = await Order.find()
            .populate('user', 'username')
            .sort({ createdAt: -1 })
            .limit(5);

        res.json({
            totalOrders,
            totalRevenue: totalRevenue[0]?.total || 0,
            recentOrders
        });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

module.exports = router;