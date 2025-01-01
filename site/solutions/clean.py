import os
import re

def remove_comments_from_java(file_path):
    """Remove Java comments from the given file."""
    with open(file_path, 'r') as f:
        content = f.read()

    pattern = r'(//.*?$|/\*.*?\*/|/\*.*?$)'
    cleaned_content = re.sub(pattern, '', content, flags=re.MULTILINE|re.DOTALL)
    with open(file_path, 'w') as f:
        f.write(cleaned_content)

def main():
    for root, _, files in os.walk('.'):
        for file_name in files:
            if file_name.endswith('.java'):
                file_path = os.path.join(root, file_name)
                remove_comments_from_java(file_path)
                print(f"Removed comments from {file_path}")

if __name__ == "__main__":
    main()
