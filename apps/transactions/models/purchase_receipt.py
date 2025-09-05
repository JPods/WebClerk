# purchase = the purchasing document (original PO)
# purchase_line = line items on the purchase (PO lines)
# purchase_receipt = a received shipment (can cover partials; add receipt_no / dt_received) 
# inventory_layer (for FIFO/LIFO buckets) tied to receipt and is the receipt_line. If there are landing costs, etc... these get assign by the receipt to the various inventory_layers.