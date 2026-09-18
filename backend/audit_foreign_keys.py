import os
import ast

compliant = []
non_compliant = []

def is_model_class(node):
    if isinstance(node, ast.ClassDef):
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == 'Model':
                return True
            elif isinstance(base, ast.Attribute) and base.attr == 'Model':
                return True
    return False

def find_foreign_keys(tree, filepath):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and is_model_class(node):
            for item in node.body:
                if isinstance(item, ast.Assign) and len(item.targets) == 1 and isinstance(item.targets[0], ast.Name):
                    field_name = item.targets[0].id
                    if isinstance(item.value, ast.Call):
                        func = item.value.func
                        is_fk = False
                        if isinstance(func, ast.Name) and func.id == 'ForeignKey':
                            is_fk = True
                        elif isinstance(func, ast.Attribute) and func.attr == 'ForeignKey':
                            is_fk = True
                        if is_fk:
                            # check name
                            if field_name.startswith('id_'):
                                non_compliant.append((filepath, field_name, 'starts with id_'))
                                continue
                            # check db_column
                            db_column = None
                            for kw in item.value.keywords:
                                if kw.arg == 'db_column':
                                    if hasattr(kw.value, 's'):  # Python < 3.8
                                        db_column = kw.value.s
                                    elif isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                                        db_column = kw.value.value
                            if db_column is not None and db_column != field_name + '_id':
                                non_compliant.append((filepath, field_name, f'db_column {db_column} != {field_name}_id'))
                            else:
                                compliant.append((filepath, field_name))

def scan_models():
    for root, dirs, files in os.walk('apps'):
        # Check if this directory is or contains models
        if 'models' in os.path.relpath(root, 'apps').split(os.sep) or 'models.py' in files:
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        tree = ast.parse(content, filepath)
                        find_foreign_keys(tree, filepath)
                    except Exception as e:
                        print(f"Error parsing {filepath}: {e}")

if __name__ == '__main__':
    scan_models()
    print(f"Total Compliant ForeignKeys: {len(compliant)}")
    for fp, f in compliant:
        print(f"  {fp}: {f}")
    print(f"Total Non-compliant ForeignKeys: {len(non_compliant)}")
    for fp, f, reason in non_compliant:
        print(f"  {fp}: {f} - {reason}")
