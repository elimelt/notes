# JavaScript template is now referenced directly from the actual JS file
# Use: @js.py to reference the JS file
import os

def get_taxonomy_js():
    """Load JavaScript template from the actual JS file"""
    js_path = os.path.join(os.path.dirname(__file__), "taxonomy.js")
    with open(js_path, 'r') as f:
        return f.read()

# For backward compatibility
TAXONOMY_JS = get_taxonomy_js()
