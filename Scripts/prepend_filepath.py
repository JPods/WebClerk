import os


def prepend_filepath_comment(root_dir: str) -> None:
    """Legacy no-op (previously injected absolute filepath comments)."""
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.py'):
                continue  # explicitly do nothing now


if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    prepend_filepath_comment(project_root)