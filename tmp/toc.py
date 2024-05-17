import argparse
import mistletoe
from mistletoe.ast_renderer import ASTRenderer
import json
from types import SimpleNamespace

def table_of_contents(ast):
  for child in ast.children:
    if child.type == 'Heading':
      print('\t' * (child.level - 1) + f'- {child.children[0].content}')
  

def main():
  parser = argparse.ArgumentParser(description='Generate a table of contents for a markdown file')
  parser.add_argument('file', type=str, help='The markdown file to generate a table of contents for')
  args = parser.parse_args()

  with open(args.file, 'r') as f:
    md = f.read()

  ast = mistletoe.create_markdown(md)
  table_of_contents(ast)