const express = require('express');
const Product = require('../models/Product');
const { auth } = require('../middleware/auth');

const router = express.Router();

// Get user's cart
router.get('/', auth, async (req, res) => {
    try {
        await req.user.populate('cart.product');
        
        // Calculate cart totals
        let subtotal = 0;
        const cartItems = req.user.cart.map(item => {
            const product = item.product;
            if (!product) return null;

            const price = product.salePrice;
            const itemTotal = price * item.quantity;
            subtotal += itemTotal;

            return {
                product: product,
                quantity: item.quantity,
                itemTotal: itemTotal
            };
        }).filter(item => item !== null);

        // Calculate shipping and tax
        const shipping = subtotal > 500 ? 0 : 50;
        const tax = subtotal * 0.08; // 8% tax
        const total = subtotal + shipping + tax;

        res.json({
            items: cartItems,
            subtotal: parseFloat(subtotal.toFixed(2)),
            shipping: parseFloat(shipping.toFixed(2)),
            tax: parseFloat(tax.toFixed(2)),
            total: parseFloat(total.toFixed(2))
        });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Add item to cart
router.post('/add', auth, async (req, res) => {
    try {
        const { productId, quantity = 1 } = req.body;

        const product = await Product.findById(productId);
        if (!product) {
            return res.status(404).json({ message: 'Product not found' });
        }

        if (product.stock < quantity) {
            return res.status(400).json({ 
                message: `Insufficient stock. Only ${product.stock} available.` 
            });
        }

        // Check if product already in cart
        const existingItemIndex = req.user.cart.findIndex(
            item => item.product.toString() === productId
        );

        if (existingItemIndex > -1) {
            // Update quantity
            const newQuantity = req.user.cart[existingItemIndex].quantity + quantity;
            
            if (product.stock < newQuantity) {
                return res.status(400).json({ 
                    message: `Insufficient stock. Only ${product.stock} available.` 
                });
            }
            
            req.user.cart[existingItemIndex].quantity = newQuantity;
        } else {
            // Add new item
            req.user.cart.push({ product: productId, quantity });
        }

        await req.user.save();
        await req.user.populate('cart.product');

        res.json({ 
            message: 'Product added to cart',
            cart: req.user.cart 
        });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Update cart item quantity
router.put('/update/:productId', auth, async (req, res) => {
    try {
        const { productId } = req.params;
        const { quantity } = req.body;

        const product = await Product.findById(productId);
        if (!product) {
            return res.status(404).json({ message: 'Product not found' });
        }

        if (quantity < 1) {
            return res.status(400).json({ message: 'Quantity must be at least 1' });
        }

        if (product.stock < quantity) {
            return res.status(400).json({ 
                message: `Insufficient stock. Only ${product.stock} available.` 
            });
        }

        const cartItem = req.user.cart.find(
            item => item.product.toString() === productId
        );

        if (!cartItem) {
            return res.status(404).json({ message: 'Product not found in cart' });
        }

        cartItem.quantity = quantity;
        await req.user.save();

        res.json({ 
            message: 'Cart updated successfully',
            cart: req.user.cart 
        });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Remove item from cart
router.delete('/remove/:productId', auth, async (req, res) => {
    try {
        const { productId } = req.params;

        req.user.cart = req.user.cart.filter(
            item => item.product.toString() !== productId
        );

        await req.user.save();

        res.json({ 
            message: 'Product removed from cart',
            cart: req.user.cart 
        });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Clear cart
router.delete('/clear', auth, async (req, res) => {
    try {
        req.user.cart = [];
        await req.user.save();

        res.json({ message: 'Cart cleared successfully' });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

module.exports = router;