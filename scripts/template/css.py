# CSS template is now referenced directly from styles.css
# Use: @css.py to reference the CSS file
import os

def get_styles_template():
    """Load CSS template from the actual CSS file"""
    css_path = os.path.join(os.path.dirname(__file__), "styles.css")
    with open(css_path, 'r') as f:
        return f.read()

# For backward compatibility
STYLES_TEMPLATE = get_styles_template()
