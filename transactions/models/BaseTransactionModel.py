from django.db import models
from common.models import BaseModel
from decimal import Decimal
'''
 Google Doc for BaseLineModel schema and design:
 https://docs.google.com/document/d/12C8LHt8x1Bl6spM_iHFC6DK01eIxQzD5_4-3cK9ybow/edit?tab=t.0
 
'''

BASE_DECIMAL_DEFAULT = Decimal("0.00")
BASE_INT_DEFAULT = Decimal("0")


from typing import Any, Dict, Optional
from pydantic import BaseModel
import time  # For timestamps, assuming Unix timestamps as in your example

class TransactionBaseModel(BaseModel):
    
    
    """
    Base Pydantic model for transactions (proposals, orders, etc.).
    This includes JSONB fields: metadata, refs, prefs, comments.
    We populate them with structured defaults or provided data upon instantiation.
    """
    metadata: Dict[str, Any] = {}  # e.g., {"history": {"created": {"by": "name", "dt": 0}}}
    refs: Dict[str, Any] = {}      # For references like IDs, e.g., {"company_id": 123, "bill_to": {...}}
    prefs: Dict[str, Any] = {}     # For preferences, e.g., {"currency": "USD", "terms": "Net 30"}
    comments: Dict[str, Any] = {}  # e.g., {"main": "Text", "alert": "Alert", or array of notes}

    def __init__(self, **data: Any):
        """
        Override init to populate JSONBs with defaults if not provided.
        This ensures structure each time the model is instantiated.
        """
        super().__init__(**data)
        self.metadata = self._populate_metadata(
            data.get('metadata', {}),
            created_by=data.get('created_by', 'system'),  # Default or from kwargs
            created_dt=data.get('created_dt', int(time.time()))  # Default to now
        )
        self.refs = self._populate_refs(data.get('refs', {}))
        self.prefs = self._populate_prefs(data.get('prefs', {}))
        self.comments = self._populate_comments(data.get('comments', {}))

    @staticmethod
    def _populate_metadata(existing: Dict[str, Any], created_by: str, created_dt: int) -> Dict[str, Any]:
        """
        Populate or update metadata JSONB with structured history.
        Ensures 'history' key exists with at least 'created' entry.
        If existing has data, merge intelligently (e.g., add 'updated' if applicable).
        """
        metadata = existing.copy()
        history = metadata.get('history', {})
        
        # Ensure 'created' is set
        if 'created' not in history:
            history['created'] = {'by': created_by, 'dt': created_dt}
        
        # Example: Add 'updated' if this is an update (logic can be expanded based on context)
        if 'id' in existing:  # Assuming 'id' indicates an existing record
            history['updated'] = {'by': 'system', 'dt': int(time.time())}  # Or pass updated_by
        
        metadata['history'] = history
        # Add other metadata keys if needed, e.g., metadata['version'] = 1
        
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
            'company_id': [],
            'contact_id': [],
            'location_id': [],
            'phone_id': [],
            'email_id': [],
            'attention': ''
        })
        

        # Pre-structured ship_to
        refs.setdefault('ship_to', {
            'company': '',
            'company_id': [],
            'contact_id': [],
            'location_id': [],
            'phone_id': [],
            'email_id': [],
            'attention': ''
        })

        # Expanded parties structure
        refs.setdefault('parties', {
            'created':   {'id': None, 'attention': ''},
            'updated':   {'id': None, 'attention': ''},
            'action':    {'id': None, 'attention': ''},
            'requested': {'id': None, 'attention': ''},
            'approved':  {'id': None, 'attention': ''},
            'packed':    {'id': None, 'attention': ''}
        })

        
        # Ensure structured sub-keys if not present
        refs.setdefault('campaign', {'id': None})
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
        #     comments['notes'] = [{'text': '', 'type': 'main', 'by': 'system', 'dt': int(time.time())}]
        
        return comments

    # Example method to update JSONBs post-instantiation, e.g., on save or edit
    def update_metadata(self, updated_by: str, additional_data: Optional[Dict[str, Any]] = None):
        """Update metadata with new 'updated' history entry."""
        history = self.metadata.get('history', {})
        history['updated'] = {'by': updated_by, 'dt': int(time.time())}
        self.metadata['history'] = history
        if additional_data:
            self.metadata.update(additional_data)

    # Similar update methods for other JSONBs can be added, e.g., add_comment(type: str, text: str)
    def add_comment(self, comment_type: str, text: str, by: str = 'system'):
        """Add a new comment entry."""
        self.comments[comment_type] = text  # Or append to array: self.comments['notes'].append({...})
