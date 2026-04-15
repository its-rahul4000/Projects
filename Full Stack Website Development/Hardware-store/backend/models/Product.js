const mongoose = require('mongoose');

const productSchema = new mongoose.Schema({
    name: {
        type: String,
        required: true,
        trim: true
    },
    description: {
        type: String,
        required: true
    },
    price: {
        type: Number,
        required: true,
        min: 0
    },
    originalPrice: {
        type: Number,
        min: 0
    },
    category: {
        type: String,
        required: true,
        enum: ['Tools', 'Electrical', 'Plumbing', 'Paint', 'Hardware', 'Safety', 'Garden', 'Building Materials']
    },
    subcategory: String,
    brand: String,
    image: {
        type: String,
        default: '/images/placeholder.jpg'
    },
    images: [String],
    stock: {
        type: Number,
        required: true,
        min: 0,
        default: 0
    },
    sku: {
        type: String,
        unique: true
    },
    features: [String],
    specifications: Map,
    featured: {
        type: Boolean,
        default: false
    },
    onSale: {
        type: Boolean,
        default: false
    },
    discount: {
        type: Number,
        min: 0,
        max: 100,
        default: 0
    },
    rating: {
        type: Number,
        min: 0,
        max: 5,
        default: 0
    },
    reviewCount: {
        type: Number,
        default: 0
    }
}, {
    timestamps: true
});

// Virtual for sale price
productSchema.virtual('salePrice').get(function() {
    if (this.onSale && this.discount > 0) {
        return this.price * (1 - this.discount / 100);
    }
    return this.price;
});

module.exports = mongoose.model('Product', productSchema);