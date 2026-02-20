#!/usr/bin/env python
"""Test script for model_name_resolver utility."""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
django.setup()

from apps.core.utils.model_name_resolver import resolve_model_name, parse_restful_path

# Test various formats
tests = [
    ('order', 'order'),
    ('Order', 'order'),
    ('purchase', 'purchase'),
    ('invoice', 'invoice'),
    ('Purchase', 'purchase'),
]

print('Testing resolve_model_name:')
for input_val, expected in tests:
    result = resolve_model_name(input_val)
    status = '✓' if result == expected else '✗'
    print(f'  {status} resolve_model_name("{input_val}") -> "{result}" (expected: "{expected}")')

print()
print('Testing parse_restful_path:')
paths = [
    '/api/transactions/order/22',
    '/transactions/order/detail/22',
    '/api/order/22',
]
for path in paths:
    result = parse_restful_path(path)
    print(f'  parse_restful_path("{path}")')
    print(f'    -> {result}')

print()
print('All tests completed!')
