# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/Scripts/prepend_filepath.py
import os

def prepend_filepath_comment(root_dir):
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.py'):
                file_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(file_path, root_dir)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Skip if already has a filepath comment
                if content.startswith('# filepath:'):
                    continue
                # Prepend the filepath comment
                new_content = f"# filepath: {file_path}\n{content}"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Prepended to {file_path}")

if __name__ == "__main__":
    project_root = "/Users/williamjames/Documents/CommerceExpert/webClerk3"
    prepend_filepath_comment(project_root)