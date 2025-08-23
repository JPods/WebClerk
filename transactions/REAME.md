# Transactions Module

transactions/
├── __init__.py
├── admin.py
├── apps.py
├── models/
│   ├── __init__.py
│   ├── proposal.py
│   ├── order.py
│   ├── invoice.py
│   ├── purchase.py
│   ├── workorder.py
│   ├── line.py
│   └── baseline.py
├── views/
│   ├── __init__.py
│   ├── proposal.py
│   ├── order.py
│   ├── invoice.py
│   ├── purchase.py
│   ├── workorder.py
├── services/
│   ├── __init__.py
├── general/
│   ├── __init__.py
│   └── line_flow.py   # For line management logic (like LineFlowManager)
│   ├── utils.py
├── order/
│   ├── __init__.py
│   ├── creation.py
│   ├── validation.py
├── invoice/
│   ├── __init__.py
│   ├── creation.py
│   ├── sync.py
├── purchase/
│   ├── __init__.py
│   └── ...
├── workorder/
│   ├── __init__.py
│   └── ...
├── forms.py
├── urls.py
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_views.py
│   ├── test_behaviors.py
├── templates/
│   └── transactions/
│       └── ...