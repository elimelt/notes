import os

def get_base_template():
    """Load base HTML template from the actual HTML file"""
    html_path = os.path.join(os.path.dirname(__file__), "base.html")
    with open(html_path, 'r') as f:
        return f.read()

def get_index_template():
    """Load index HTML template from the actual HTML file"""
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, 'r') as f:
        return f.read()

# For backward compatibility
BASE_TEMPLATE = get_base_template()
INDEX_TEMPLATE = get_index_template()
