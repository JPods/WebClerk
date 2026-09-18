-- SQL function to display Item.quantity in logical order for human reading
-- Run this manually or include in a migration
--
-- Usage:
--   SELECT id, sku, quantity_ordered(quantity) FROM products_item;
--
-- Or create a view:
--   CREATE VIEW items_readable AS 
--   SELECT id, sku, name, quantity_ordered(quantity) as quantity 
--   FROM products_item;

CREATE OR REPLACE FUNCTION quantity_ordered(q jsonb)
RETURNS jsonb AS $$
BEGIN
    RETURN jsonb_build_object(
        -- Physical inventory
        'on_hand', COALESCE(q->>'on_hand', '0')::int,
        'available', COALESCE(q->>'available', '0')::int,
        'allocated', COALESCE(q->>'allocated', '0')::int,
        -- Defaults
        'sell_default', COALESCE(q->>'sell_default', '1')::int,
        'purchase_default', COALESCE(q->>'purchase_default', '1')::int,
        -- Transaction buckets
        'on_po', COALESCE(q->>'on_po', '0')::int,
        'on_wo', COALESCE(q->>'on_wo', '0')::int,
        'on_so', COALESCE(q->>'on_so', '0')::int,
        'invoiced', COALESCE(q->>'invoiced', '0')::int
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Optional: Create a readable view
-- CREATE OR REPLACE VIEW products_item_readable AS
-- SELECT 
--     id, 
--     sku, 
--     name,
--     quantity_ordered(quantity) as quantity
-- FROM products_item;
