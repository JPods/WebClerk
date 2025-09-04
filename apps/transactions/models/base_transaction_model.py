from common.models import BaseModel  # Your Django base model
from typing import Any, Dict, Optional
from pydantic import BaseModel
from decimal import Decimal
import time

def utc_ts():
    """Return current UTC timestamp as integer."""
    return int(time.time())

'''
 Google Doc for BaseLineModel schema and design:
 https://docs.google.com/document/d/12C8LHt8x1Bl6spM_iHFC6DK01eIxQzD5_4-3cK9ybow/edit?tab=t.0
 
'''

BASE_DECIMAL_DEFAULT = Decimal("0.00")
BASE_INT_DEFAULT = Decimal("0")



# Removed duplicate definition of default_transaction_flow

def default_source():
    return {
        "campaign_id": 0,
        "catalog_id": None,
        "vendor_id": 0,
        "manufacturer_id": 0,
        # tracks the how we got this transaction and where it was resolved
        # mostly at the transaction level unless split across multiple entities
        # proposal to order, order to purchase or invoice, etc...
        "source": [{"type": "", "id": 0}],
        "destination": [{"type": "", "id": 0}]
    }

def default_comments():
    return {
        "public": "",
        "process": "",
        "foreign": ""
    }

def default_physical():
    return {
        "unit": 0,
        "extended": 0,
        "volume":{},
        "hazardous": {}
    }






class TransactionBaseModel(BaseModel):
    """
    Base Pydantic model for transactions (proposals, orders, etc.).
    This includes JSONB fields: metadata, refs, prefs, comments.
    We populate them with structured defaults or provided data upon instantiation.
    """
    priority: str  # Priority as a string field
    # Flat fields for fast queries
    customer_id: int = 0
    manufacturer_id: int = 0
    vendor_id: int = 0
    # true until all conditions for the transaction are met
    # e.g., payment received, items shipped, etc.
    is_active: bool = True
    is_deleted: bool = False
    is_archived: bool = False
    metadata: Dict[str, Any] = {}  # e.g., {"history": {"created": {"by": "name", "dt": 0}}}
    tax: Dict[str, Any] = {}
    total: Dict[str, Any] = {}
    amount: Dict[str, Any] = {}
    ship: Dict[str, Any] = {}
    refs: Dict[str, Any] = {}      # For references like IDs, e.g., {"company_id": 123, "bill_to": {...}}
    prefs: Dict[str, Any] = {}     # For preferences, e.g., {"currency": "USD", "terms": "Net 30"}
    comments: Dict[str, Any] = {}  # e.g., {"main": "Text", "alert": "Alert", or array of notes}

    def __init__(self, **data: Any):
        super().__init__(**data)
        self.metadata = self._populate_metadata(
            data.get('metadata', {}),
            created_by=data.get('created_by', 'system'),  # Default or from kwargs
            dt_created=data.get('dt_created', int(utc_ts()))  # Default to now
        )
        self.tax = self._populate_tax(data.get('tax', {}))
        self.total = self._populate_total(data.get('total', {}))
        self.amount = self._populate_amount(data.get('amount', {}))
        self.ship = self._populate_ship(data.get('ship', {}))
        self.refs = self._populate_refs(data.get('refs', {}))
        self.prefs = self._populate_prefs(data.get('prefs', {}))
        self.comments = self._populate_comments(data.get('comments', {}))

    @staticmethod
    def _populate_metadata(existing: Dict[str, Any], created_by: str, dt_created: int) -> Dict[str, Any]:
        """
        Populate or update metadata JSONB with structured history.
        Ensures 'history' key exists with at least 'created' entry.
        If existing has data, merge intelligently (e.g., add 'updated' if applicable).
        """
        metadata = existing.copy()
        history = metadata.get('history', {})
        
        # Ensure 'created' is set
        if 'created' not in history:
            history['created'] = {'by': created_by, 'dt': dt_created}
        
        # Example: Add 'updated' if this is an update (logic can be expanded based on context)
        if 'id' in existing:  # Assuming 'id' indicates an existing record
            history['updated'] = {'by': 'system', 'dt': utc_ts()}  # Or pass updated_by
        
        metadata['history'] = history
        # Add other metadata keys if needed, e.g., metadata['version'] = 1
    # Expanded parties structure
        metadata.setdefault('history', {
            'created':   {'contact_id': None, 'attention': '', "dt": None},
            'updated':   {'contact_id': None, 'attention': '', "dt": None},
            'action':    {'contact_id': None, 'attention': '', "dt": None},
            'requested': {'contact_id': None, 'attention': '', "dt": None},
            'approved':  {'contact_id': None, 'attention': '', "dt": None},
            'packed':    {'contact_id': None, 'attention': '', "dt": None},
            'printed':    [{'form_id': None, 'form_name':'', 'contact_id': None, 'attention': '', "dt": None}]
        })

        metadata.setdefault('forms', [{
            'id': 0,
            'name': '',
            'purpose': ''
        }])

        return metadata

    @staticmethod
    def _populate_refs(existing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Populate or structure refs JSONB.
        This can include references like company_id, bill_to, ship_to, etc.
        Defaults to empty dict; structure based on your schema recommendations.
        """
        refs = existing.copy()
        
        # Pre-structured bill_to
        # e.g., {'company_bill_to': '', 'company_billto_id': [], 'contact_billto_id': [], ...}
        refs.setdefault('bill_to', {
            'company': '',
            'attention': '',
            'email': '',
            'phone': '',
            'company_id': [],
            'contact_id': [],
            'location_id': [],
            'phone_id': [],
            'email_id': [],
        })
        
        # Pre-structured ship_to
        refs.setdefault('ship_to', {
            'company': '',
            'attention': '',
            'email': '',
            'phone': '',
            'company_id': [],
            'contact_id': [],
            'location_id': [],
            'phone_id': [],
            'email_id': [],
        })

 


        # Ensure structured sub-keys if not present
        refs.setdefault('campaign', {'name': '', 'id': None})
        # Add more defaults as per your fields, e.g., refs['boilerplate_id'] = None
        
        return refs

    @staticmethod
    def _populate_prefs(existing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Populate or structure prefs JSONB for preferences.
        Examples: currency, payment terms, shipping prefs, etc.
        Defaults to common values.
        """
        prefs = existing.copy()
        
        # Set defaults if keys are missing
        prefs.setdefault('currency', {'code': 'USD', 'rate': 1.0})
        prefs.setdefault('payment_terms', {'name':'Net 30','id': None})
        prefs.setdefault('ship_via', 'UPS')  # Or embed in ship_to if preferred
        prefs.setdefault('tax', {'rate': 0.0, 'jurisdiction': 'Default'})
        # Add more like 'priority': 'Medium', 'overruns_allowed': False
        prefs.setdefault('commissions', [])

        return prefs

    @staticmethod
    def _populate_comments(existing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Populate or structure comments JSONB.
        Can be a dict of types or an array for multiple notes.
        If volume is high, suggest linking to action records externally.
        """
        comments = existing.copy()
        
        # Option 1: Simple dict structure
        comments.setdefault('public', '')
        comments.setdefault('alert', '')
        comments.setdefault('process', '')
        comments.setdefault('by_other', '')
        
        # Option 2: Array for history/threading (more flexible for variability)
        # if not isinstance(comments.get('notes'), list):
        #     comments['notes'] = [{'text': '', 'type': 'main', 'by': 'system', 'dt': utc_ts()}]
        
        return comments

    @staticmethod
    def _populate_tax(existing: Dict[str, Any]) -> Dict[str, Any]:
        tax = existing.copy()
        tax.setdefault('exempt_code', '')
        tax.setdefault('jurisdiction', '')
        tax.setdefault('on_cost', 0.0)
        tax.setdefault('on_sales', 0.0)
        tax.setdefault('rate', 0.0)
        tax.setdefault('total', 0.0)
        return tax

    @staticmethod
    def _populate_total(existing: Dict[str, Any]) -> Dict[str, Any]:
        total = existing.copy()
        total.setdefault('time', 0.0)
        total.setdefault('total', 0.0)
        total.setdefault('cost', 0.0)
        total.setdefault('materials', 0.0)
        total.setdefault('workorders', 0.0)
        total.setdefault('landed', 0.0)
        total.setdefault('tendered', 0.0)
        total.setdefault('applied', 0.0)
        total.setdefault('due', 0.0)
        total.setdefault('margins', 0.0)
        return total

    @staticmethod
    def _populate_amount(existing: Dict[str, Any]) -> Dict[str, Any]:
        amount = existing.copy()
        amount.setdefault('amount', 0.0)
        amount.setdefault('force_value', 0.0)
        amount.setdefault('backlog', 0.0)
        amount.setdefault('cancel', 0.0)
        amount.setdefault('other', 0.0)
        amount.setdefault('discount', 0.0)
        amount.setdefault('balance_due', 0.0)
        return amount

    @staticmethod
    def _populate_ship(existing: Dict[str, Any]) -> Dict[str, Any]:
        ship = existing.copy()
        ship.setdefault('handling', 0.0)
        ship.setdefault('adjustment', 0.0)
        ship.setdefault('freight_cost', 0.0)
        ship.setdefault('other_cost', 0.0)
        ship.setdefault('total', 0.0)
        ship.setdefault('weight', 0.0)
        ship.setdefault('via', '')
        ship.setdefault('instruction', '')
        ship.setdefault('is_auto', False)
        ship.setdefault('is_partial', False)
        return ship

    @staticmethod
    def _populate_count(existing: Dict[str, Any]) -> Dict[str, Any]:
        count = existing.copy()
        count.setdefault('views', 0)
        count.setdefault('items', 0)
        count.setdefault('items_backlog', 0)
        count.setdefault('labels', 0)
        count.setdefault('lines', 0)
        count.setdefault('printed', 0)
        count.setdefault('lines_index', 0)
        return count

    # Example method to update JSONBs post-instantiation, e.g., on save or edit
    def update_metadata(self, updated_by: str, additional_data: Optional[Dict[str, Any]] = None):
        """Update metadata with new 'updated' history entry."""
        history = self.metadata.get('history', {})
        history['updated'] = {'by': updated_by, 'dt': utc_ts()}
        self.metadata['history'] = history
        if additional_data:
            self.metadata.update(additional_data)

    # Similar update methods for other JSONBs can be added, e.g., add_comment(type: str, text: str)
    def add_comment(self, comment_type: str, text: str, by: str = 'system'):
        """Add a new comment entry."""
        self.comments[comment_type] = text  # Or append to array: self.comments['notes'].append({...})
