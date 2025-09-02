import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from core.views.related_view import get_related_data  # Adjust the import path as needed

result = get_related_data(
    'contacts',
    6,
    related_tables_dict={'contacts': ['phones', 'emails']},
    pagination={'phones': {'page': 2, 'page_size': 5}}
)
if result['errors']:
    print("Some errors:", result['errors'])
else:
    print(result['related'])