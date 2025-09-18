Split the BastTranstaction model
all transactions will have costs
purchase_order and work_order models do not have sell functions.
I think we should look at spilting a totals object into the dictionaries of:

totals for highly searched and acted on
def default_totals() -> Dict[str, Any]:
    return {
        "amount": None,
        "margin": None,
        "margin_pc": None,
        "total": None

        #limited to order and invoice
        "received": None,
        "unapplied": None,
        "balance": None,
    }

accumulate costs
def default_costs() -> Dict[str, Any]:
    return {
        "line_sum_goods": None,
        "line_sum_tax": None,
        "line_sum_shipping": None,
        "line_sum_handling": None,
        "handling": None,
        "freight": None,
        "tax_rate": None,
        "tax": None,
        "commissions": None,
        "total": None
    }

def default_finance() -> Dict[str, Any]:
    return {
        "sales_tax_id": 0,
        "sales_tax_name": "",
        "sales_tax_rate": None,
        "sales_tax": None,
        "cost_tax_id": 0,
        "cost_tax_name": "",
        "cost_tax_rate": None,
        "cost_tax": None,
        "tax_subtotal": None,
        "tax_pc":None,
        "collection_expense": None,
        "exchange_expense": None
    }


Normally we will have setting model record define what roles can veiw and edit which fields. But we are still DROPPING the data file to often to set them up. We should set up some jsons that can be loaded as a tool today so the full records are not sent when related records are being added to record.related{}

For example, let's limit communications app fields to id and basic information such as phone number, name, email, address etc...