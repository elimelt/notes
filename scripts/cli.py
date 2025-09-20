#!/usr/bin/env python3
"""
cli.py

Unified command-line interface for all notes repository tools.
"""

import argparse
import sys
import os
import subprocess
from pathlib import Path
from typing import List, Optional

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(__file__))

class NotesCLI:
    def __init__(self):
        self.script_dir = Path(__file__).parent
        
    def run_command(self, command: str, args: List[str]) -> int:
        """Run a command with the given arguments."""
        try:
            if command == "build":
                return self._run_build(args)
            elif command == "clean":
                return self._run_clean(args)
            elif command == "embed":
                return self._run_embed(args)
            elif command == "keywords":
                return self._run_keywords(args)
            elif command == "lint":
                return self._run_lint(args)
            elif command == "merge":
                return self._run_merge(args)
            elif command == "replace":
                return self._run_replace(args)
            elif command == "search":
                return self._run_search(args)
            elif command == "serve":
                return self._run_serve(args)
            else:
                print(f"Unknown command: {command}")
                print("Use 'python scripts/cli.py help' to see available commands")
                return 1
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            return 130
        except Exception as e:
            print(f"Error running {command}: {e}")
            return 1
    
    def _run_build(self, args: List[str]) -> int:
        """Build the static site."""
        build_script = self.script_dir / "build.py"
        if not build_script.exists():
            print("Build script not found")
            return 1
        
        cmd = [sys.executable, str(build_script)] + args
        return subprocess.run(cmd).returncode
    
    def _run_clean(self, args: List[str]) -> int:
        """Clean the site directory."""
        clean_script = self.script_dir / "clean.py"
        if not clean_script.exists():
            print("Clean script not found")
            return 1
        
        cmd = [sys.executable, str(clean_script)] + args
        return subprocess.run(cmd).returncode
    
    def _run_embed(self, args: List[str]) -> int:
        """Generate embeddings for markdown files."""
        embed_script = self.script_dir / "embed.py"
        if not embed_script.exists():
            print("Embed script not found")
            return 1
        
        cmd = [sys.executable, str(embed_script)] + args
        return subprocess.run(cmd).returncode
    
    def _run_keywords(self, args: List[str]) -> int:
        """Extract keywords from markdown files."""
        keywords_script = self.script_dir / "keywords.py"
        if not keywords_script.exists():
            print("Keywords script not found")
            return 1
        
        cmd = [sys.executable, str(keywords_script)] + args
        return subprocess.run(cmd).returncode
    
    def _run_lint(self, args: List[str]) -> int:
        """Lint markdown files for issues."""
        lint_script = self.script_dir / "lint.py"
        if not lint_script.exists():
            print("Lint script not found")
            return 1
        
        cmd = [sys.executable, str(lint_script)] + args
        return subprocess.run(cmd).returncode
    
    def _run_merge(self, args: List[str]) -> int:
        """Merge metadata from files."""
        merge_script = self.script_dir / "merge_meta.py"
        if not merge_script.exists():
            print("Merge script not found")
            return 1
        
        cmd = [sys.executable, str(merge_script)] + args
        return subprocess.run(cmd).returncode
    
    def _run_replace(self, args: List[str]) -> int:
        """Replace characters in markdown files."""
        replace_script = self.script_dir / "replace.py"
        if not replace_script.exists():
            print("Replace script not found")
            return 1
        
        cmd = [sys.executable, str(replace_script)] + args
        return subprocess.run(cmd).returncode
    
    def _run_search(self, args: List[str]) -> int:
        """Search markdown content using embeddings."""
        search_script = self.script_dir / "search.py"
        if not search_script.exists():
            print("Search script not found")
            return 1
        
        cmd = [sys.executable, str(search_script)] + args
        return subprocess.run(cmd).returncode
    
    def _run_serve(self, args: List[str]) -> int:
        """Serve the static site locally."""
        serve_script = self.script_dir / "serve.py"
        if not serve_script.exists():
            print("Serve script not found")
            return 1
        
        cmd = [sys.executable, str(serve_script)] + args
        return subprocess.run(cmd).returncode

def print_help():
    """Print help information for all commands."""
    print("Notes Repository CLI")
    print("===================")
    print()
    print("Available commands:")
    print()
    
    commands = [
        ("build", "Build the static site from markdown files"),
        ("clean", "Clean the site directory"),
        ("embed", "Generate embeddings for markdown files"),
        ("keywords", "Extract keywords from markdown files"),
        ("lint", "Lint markdown files for issues"),
        ("merge", "Merge metadata from files"),
        ("replace", "Replace characters in markdown files"),
        ("search", "Search markdown content using embeddings"),
        ("serve", "Serve the static site locally"),
    ]
    
    for cmd, desc in commands:
        print(f"  {cmd:<10} - {desc}")
    
    print()
    print("Usage:")
    print("  python scripts/cli.py <command> [options]")
    print()
    print("Quick examples:")
    print("  python scripts/cli.py build                    # Build the site")
    print("  python scripts/cli.py search --query 'algorithms'  # Search content")
    print("  python scripts/cli.py lint --recursive content/    # Lint all files")
    print("  python scripts/cli.py serve                        # Start local server")
    print("  python scripts/cli.py clean                         # Clean build files")
    print()
    print("For detailed help on a specific command:")
    print("  python scripts/cli.py <command> --help")
    print()
    print("Common workflows:")
    print("  1. Clean and build:     cli clean && cli build")
    print("  2. Lint and fix:        cli lint content/ && cli replace --interactive")
    print("  3. Search and serve:    cli search --rebuild && cli serve")

def main():
    if len(sys.argv) < 2:
        print_help()
        return 0
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    if command in ["-h", "--help", "help"]:
        print_help()
        return 0
    
    cli = NotesCLI()
    return cli.run_command(command, args)

if __name__ == "__main__":
    sys.exit(main())
