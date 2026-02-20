Now lets get the transfer between transactions working

In a flow from proposal to proposal
1. a null id proposal is created
2. Customer information is not populated from the proposal, price_level is set to "retail"
3. Lines are copied with 
	proposal_line.quantity.placed = proposal_line.quantity.placed
	proposal_line.quantity.actioned = 0
	proposal_line.quantity.remaining = proposal_line.quantity.placed

When the customer is selected, the appropriate price_level will be set and the lines recalculate.

From proposal to order or invoice.
1. a null id order or invoice is created
2. parent_model and parent_id is set.
2. Customer information is populated from the proposal to the order.
3. Line-Items that are copied into order lines.
	Line data is transferred to such as .refs.links.document[], contact, action,....
	Line data having to do with dates are reset
	if quantity.increment = 0;
		order_line.quantity.placed = proposal.quantity.remaining
		proposal_line.quantity.actioned = proposal.quantity.remaining
		proposal_line.quantity.remaining = 0
	else;
	If (proposal.quantity.increment < proposal.quantity.remaining) 
		order_line.quantity.placed = proposal.quantity.increment
		proposal_line.quantity.actioned =+ proposal.quantity.remaining
		proposal_line.quantity.remaining =- proposal.quantity.remaining
	 else
		order_line.quantity.placed = proposal.quantity.remaining
		proposal_line.quantity.actioned =+ proposal.quantity.remaining
		proposal_line.quantity.remaining = 0
		
		
In a flow from proposal to purchase, or order to purchase, or invoice to purchase, or purchase to proposal,  or purchase to order, or purchase to invoice
1. a null id purchase is created
2. Customer information is not populated from the proposal, Vendor information will be entered or the reverse from purchase
3. Lines are copied with to (receiving_line is receiving information, original_line is providing information)
	receiving_line.quantity.placed = original_line.quantity.placed
	receiving_line.quantity.actioned = 0
	receiving_line.quantity.remaining = original_line.quantity.placed
	
	