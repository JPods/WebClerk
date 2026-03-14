/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useState, useEffect } from "react";
import { getRecords } from "../../../../../api/wcapi";

interface Product {
  id: number;
  name: string;
  description?: string;
  sku?: string;
  price?: {
    sell?: number;
    cost?: number;
  };
}

interface ProductSelectProps {
  value?: number;
  onChange: (productId: number | undefined, product?: Product) => void;
  placeholder?: string;
  disabled?: boolean;
}

export default function ProductSelect({ value, onChange, placeholder = "Select product", disabled = false }: ProductSelectProps) {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    try {
      setLoading(true);
      const response = await getRecords('item', { limit: 100 });
      const productData = response.results.map((p: any) => ({
        id: p.id,
        name: p.item?.description || p.name || 'Unnamed Product',
        description: p.item?.description_text,
        sku: p.item?.sku,
        price: p.price || {}
      }));
      setProducts(productData);
    } catch (error) {
      console.error('Failed to load products:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredProducts = products.filter(product =>
    product.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    product.sku?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    product.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const selectedProduct = products.find(p => p.id === value);

  const handleSelect = (product: Product) => {
    onChange(product.id, product);
    setIsOpen(false);
    setSearchTerm("");
  };

  const handleClear = () => {
    onChange(undefined);
    setSearchTerm("");
  };

  return (
    <div className="relative">
      <div className="relative">
        <input
          type="text"
          value={selectedProduct ? selectedProduct.name : searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            if (!isOpen) setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onBlur={() => setTimeout(() => setIsOpen(false), 200)}
          placeholder={placeholder}
          disabled={disabled}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white dark:border-gray-600"
        />
        {selectedProduct && !disabled && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-8 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            ×
          </button>
        )}
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          disabled={disabled}
          className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
        >
          ▼
        </button>
      </div>

      {isOpen && (
        <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto dark:bg-gray-800 dark:border-gray-600">
          {loading ? (
            <div className="px-3 py-2 text-gray-500 dark:text-gray-400">Loading products...</div>
          ) : filteredProducts.length === 0 ? (
            <div className="px-3 py-2 text-gray-500 dark:text-gray-400">No products found</div>
          ) : (
            filteredProducts.map((product) => (
              <div
                key={product.id}
                onClick={() => handleSelect(product)}
                className="px-3 py-2 hover:bg-gray-100 cursor-pointer dark:hover:bg-gray-700"
              >
                <div className="font-medium dark:text-white">
                  {product.name}
                </div>
                {product.sku && (
                  <div className="text-sm text-gray-500 dark:text-gray-400">SKU: {product.sku}</div>
                )}
                {product.price?.sell && (
                  <div className="text-sm text-green-600 dark:text-green-400">
                    ${Number(product.price.sell).toFixed(2)}
                  </div>
                )}
                {product.description && (
                  <div className="text-sm text-gray-500 dark:text-gray-400 truncate">
                    {product.description}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}