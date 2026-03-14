/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React from "react";

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

const Test: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <section className="bg-gradient-to-r from-gray-900 via-black to-gray-800 text-white py-20 text-center">
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-wide">
          Freshness Delivered in Minutes 🚀
        </h1>
        <p className="mt-4 text-lg text-gray-300">
          Groceries, fruits, snacks & more. Faster than ever.
        </p>
        <div className="mt-6">
          <button className="px-6 py-3 bg-pink-500 hover:bg-pink-600 text-white text-lg rounded-lg shadow-lg">
            Start Shopping
          </button>
        </div>
      </section>

      {/* Deals Banner */}
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

      {/* Category Grid */}
      <section className="max-w-6xl mx-auto py-12 px-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-6">Shop by Category</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
          {categories.map((cat, i) => (
            <div
              key={i}
              className="flex flex-col items-center justify-center p-6 bg-white rounded-xl shadow hover:shadow-lg transition transform hover:-translate-y-1"
            >
              <span className="text-4xl mb-2">{cat.icon}</span>
              <p className="font-medium text-gray-700">{cat.name}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Product Highlights */}
      <section className="bg-gray-100 py-12 px-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-8 text-center">
          Featured Products ✨
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {["Organic Apples 🍏", "Classic Cola 🥤", "Clean & Fresh Detergent 🧼"].map((item, i) => (
            <div
              key={i}
              className="bg-white rounded-xl p-6 shadow hover:shadow-xl hover:scale-105 transition"
            >
              <h3 className="text-lg font-semibold mb-2">{item}</h3>
              <p className="text-gray-600">Special deal available</p>
              <button className="mt-4 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg text-sm">
                Add to Cart
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-6 text-center mt-8">
        <p>© {new Date().getFullYear()} FreshMart – Inspired by Zepto, DealShare & BigBasket</p>
      </footer>
    </div>
  );
};

export default Test;
