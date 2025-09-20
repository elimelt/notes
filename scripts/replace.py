import argparse
import subprocess
import tempfile
import os


def collect_md_files(paths, recursive=False):
    """Collect .md files from the provided paths."""
    collected = []
    for path in paths:
        if os.path.isfile(path) and path.endswith(".md"):
            collected.append(path)
        elif os.path.isdir(path) and recursive:
            for root, _, files in os.walk(path):
                for file in files:
                    if file.endswith(".md"):
                        collected.append(os.path.join(root, file))
    return collected


def replace_chars(input_files, backup, replacements):
    if not replacements:
        print("No replacements to apply.")
        return

    # generate sed script
    sed_script_lines = []
    for old_char, new_char in replacements.items():
        escaped_old = old_char.replace("/", "\\/").replace("&", "\\&")
        escaped_new = new_char.replace("/", "\\/").replace("&", "\\&")
        sed_script_lines.append(f"s/{escaped_old}/{escaped_new}/g")

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".sed") as sed_file:
        sed_file.write("\n".join(sed_script_lines))
        sed_file_path = sed_file.name

    for input_file in input_files:
        if backup:
            subprocess.run(["cp", input_file, f"{input_file}.bak"], check=True)

        output_file = f"{input_file}.tmp"
        with open(output_file, "w") as out_f:
            subprocess.run(
                ["sed", "-f", sed_file_path, input_file], stdout=out_f, check=True
            )

        os.replace(output_file, input_file)

    os.remove(sed_file_path)
    print("Replacement done.")


def find_non_ascii_characters(input_files):
    found_chars = {}
    for input_file in input_files:
        with open(input_file, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                for char in line:
                    if ord(char) > 127:
                        if char not in found_chars:
                            found_chars[char] = set()
                        found_chars[char].add((input_file, line_number))
    return found_chars


def get_replacements_interactive(input_files):
    print("🔍 Scanning files for non-ASCII characters...\n")
    found_chars = find_non_ascii_characters(input_files)

    if not found_chars:
        print("✅ No non-ASCII characters found.")
        return {}

    print("🧠 Found the following characters:\n")
    for char, locations in found_chars.items():
        print(f"Character: '{char}' (U+{ord(char):04X}) found in:")
        for file, line in sorted(locations):
            print(f"  - {file}:{line}")
        print()

    replacements = {}
    print("🛠 Now provide replacements for each character:\n")
    for char in found_chars:
        while True:
            replacement = input(f"Replace '{char}' (U+{ord(char):04X}) with: ").strip()
            if replacement == "":
                print("Replacement cannot be empty.")
            else:
                replacements[char] = replacement
                break

    return replacements


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Replace non-ASCII characters in .md files."
    )
    parser.add_argument("input_files", nargs="+", help="Markdown files or directories")
    parser.add_argument(
        "-b", "--backup", action="store_true", help="Create backup of original files"
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Enable interactive replacement mode",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recursively search directories for .md files",
    )

    args = parser.parse_args()

    # collect .md files
    input_files = collect_md_files(args.input_files, recursive=args.recursive)

    if not input_files:
        print("❌ No markdown files found.")
        exit(1)

    default_replacements = {
        "—": "-",
        "–": "-",
        "’": "'",
        "”": '"',
        "“": '"',
        "…": "...",
    }

    replacements = (
        get_replacements_interactive(input_files)
        if args.interactive
        else default_replacements
    )

    replace_chars(input_files, args.backup, replacements)
