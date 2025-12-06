
import sys
import os

def get_resource_path(relative_path_from_project_root):
    """
    Get absolute path to resource, works for dev and for PyInstaller bundled app.
    Assumes 'assets', 'docs', 'build', 'src' are at the project root.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in a PyInstaller bundle (resources are relative to _MEIPASS)
        base_path = sys._MEIPASS
    else:
        # Running in development
        # Go up from the current file's directory (e.g., src/nexus/utils/path_helpers.py)
        # to the project root (Nexus/)
        # path_helpers.py is in src/nexus/utils/
        # .. -> src/nexus/
        # .. -> src/
        # .. -> Nexus/ (Project Root)
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.abspath(os.path.join(current_file_dir, '..', '..', '..'))

    return os.path.join(base_path, relative_path_from_project_root)
