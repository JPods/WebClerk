/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React from "react";

import { FaSearchPlus, FaShoppingCart } from "react-icons/fa";
import { UserIcon } from "../../icons";


const categories = [
  { name: "Groceries", icon: "🥦" },
  { name: "Fruits", icon: "🍎" },
  { name: "Beverages", icon: "🥤" },
  { name: "Household", icon: "🧹" },
  { name: "Snacks", icon: "🍪" },
  { name: "Dairy", icon: "🥛" },
];

const deals = [
  { title: "50% Off Veggies 🥦", color: "bg-green-500" },
  { title: "Buy 1 Get 1 Snacks 🍪", color: "bg-yellow-400" },
  { title: "Flat ₹100 Off Beverages 🥤", color: "bg-pink-500" },
];

const products = [
  { name: "Organic Apples 🍏", price: "₹120/kg" },
  { name: "Classic Cola 🥤", price: "₹50" },
  { name: "Fresh Milk 🥛", price: "₹65/L" },
  { name: "Premium Rice 🍚", price: "₹800/10kg" },
  { name: "Chocolate Cookies 🍪", price: "₹75" },
  { name: "Detergent Powder 🧼", price: "₹120" },
];

const Test: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* 🔹 Navbar */}
      <header className="bg-white shadow sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          {/* Logo */}
          <h1 className="text-2xl font-bold text-green-600">FreshMart</h1>
          
          {/* Search Bar */}
          <div className="flex flex-1 mx-6 max-w-xl">
            <input
              type="text"
              placeholder="Search for products..."
              className="flex-grow px-4 py-2 border border-gray-300 rounded-l-md focus:outline-none"
            />
            <button className="bg-green-600 px-4 py-2 rounded-r-md text-white hover:bg-green-700">
  
              <FaSearchPlus className="w-5 h-5" />
            </button>
          </div>

          {/* Nav Actions */}
          <div className="flex items-center gap-6">
            <button className="flex items-center gap-1 hover:text-green-600">
              <UserIcon className="w-5 h-5" /> Login
            </button>
            <button className="flex items-center gap-1 hover:text-green-600 relative">
             
              <FaShoppingCart className="w-5 h-5" />
              <span className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full px-1 text-xs">
                3
              </span>
            </button>
          </div>
        </div>
      </header>

      {/* 🔹 Hero Section */}
      <section className="bg-gradient-to-r from-gray-900 via-black to-gray-800 text-white py-20 text-center">
        <h2 className="text-4xl md:text-5xl font-extrabold">
          Freshness Delivered in Minutes 🚀
        </h2>
        <p className="mt-3 text-lg opacity-80">
          Groceries, fruits, snacks & more. Faster than ever.
        </p>
        <div className="mt-6">
          <button className="px-6 py-3 bg-pink-500 hover:bg-pink-600 text-white text-lg rounded-lg shadow-lg">
            Start Shopping
          </button>
        </div>
      </section>

      {/* 🔹 Deals Banner */}
      <section className="py-6 bg-white shadow-md flex overflow-x-auto gap-4 px-6">
        {deals.map((deal, i) => (
          <div
            key={i}
            className={`${deal.color} text-white px-6 py-3 rounded-lg flex-shrink-0 font-semibold shadow`}
          >
            {deal.title}
          </div>
        ))}
      </section>

      {/* 🔹 Category Grid */}
      <section className="max-w-7xl mx-auto py-12 px-6">
        <h3 className="text-2xl font-bold mb-6">🛍️ Shop by Category</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
          {categories.map((cat, i) => (
            <div
              key={i}
              className="flex flex-col items-center justify-center p-6 bg-white rounded-xl shadow hover:shadow-lg transition transform hover:-translate-y-1"
            >
              <span className="text-4xl mb-2">{cat.icon}</span>
              <p className="font-medium">{cat.name}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 🔹 Featured Products */}
      <section className="bg-gray-100 py-12 px-6">
        <h3 className="text-2xl font-bold mb-8 text-center">
          Featured Products ✨
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-7xl mx-auto">
          {products.slice(0, 3).map((item, i) => (
            <div
              key={i}
              className="bg-white rounded-xl p-6 shadow hover:shadow-xl hover:scale-105 transition"
            >
              <h4 className="text-lg font-semibold mb-2">{item.name}</h4>
              <p className="text-gray-600">{item.price}</p>
              <button className="mt-4 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm">
                Add to Cart
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* 🔹 Best Sellers */}
      <section className="max-w-7xl mx-auto py-12 px-6">
        <h3 className="text-2xl font-bold mb-6">🔥 Best Sellers</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
          {products.map((p, i) => (
            <div
              key={i}
              className="bg-white rounded-lg shadow p-4 hover:shadow-lg transition"
            >
              <div className="h-24 flex items-center justify-center text-3xl">
                🛒
              </div>
              <h4 className="font-semibold mt-2">{p.name}</h4>
              <p className="text-sm text-gray-600">{p.price}</p>
              <button className="mt-3 w-full py-2 bg-pink-500 hover:bg-pink-600 text-white rounded-md text-sm">
                Add to Cart
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* 🔹 Footer */}
      <footer className="bg-gray-900 text-gray-300 py-8 mt-12">
        <div className="max-w-7xl mx-auto px-6 grid md:grid-cols-3 gap-6">
          <div>
            <h4 className="font-bold text-white mb-3">FreshMart</h4>
            <p className="text-sm">
              Fresh groceries, delivered fast. Inspired by Zepto, DealShare &
              BigBasket.
            </p>
          </div>
          <div>
            <h4 className="font-bold text-white mb-3">Quick Links</h4>
            <ul className="space-y-2 text-sm">
              <li>About Us</li>
              <li>Careers</li>
              <li>Help Center</li>
              <li>Privacy Policy</li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold text-white mb-3">Contact</h4>
            <p className="text-sm">support@freshmart.com</p>
            <p className="text-sm">+91 99999 88888</p>
          </div>
        </div>
        <p className="text-center text-gray-500 text-sm mt-6">
          © {new Date().getFullYear()} FreshMart. All rights reserved.
        </p>
      </footer>
    </div>
  );
};

export default Test;
