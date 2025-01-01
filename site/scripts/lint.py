import os
import argparse

colors = {
    'red': '\033[91m',
    'green': '\033[92m',
    'yellow': '\033[93m',
    'blue': '\033[94m',
    'purple': '\033[95m',
    'end': '\033[0m'
}

def print_c(text, color):
    print(f"{colors[color]}{text}{colors['end']}")

def lint_file(filename):

    if not filename.endswith('.md'):
        print_c(f"Skipping {filename}", 'yellow')
        return
    warncount = 0
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            line_number = 0
            for line in f:
                line_number += 1
                for char in line:
                    if ord(char) > 127:  # ASCII range is 0-127
                        warncount += 1
                        # print line number and character in green
                        print_c(f"{filename}:{line_number}:{char}", 'green')
    except UnicodeDecodeError:
        print_c(f"Skipping {filename}", 'yellow')

    return warncount

def main(filenames):
    total_warncount = 0
    for filename in filenames:
        if not filename.endswith('.md'):
            print_c(f"Skipping {filename}", 'yellow')
            continue

        print("Linting", end=' ')
        print_c(filename, 'red')
        total_warncount += lint_file(filename)

    if total_warncount > 0:
        print_c(f"Total warnings: {total_warncount}", 'red')
    else:
        print_c("No warnings found!", 'green')

def get_files_recursively(directory):
    file_paths = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_paths.append(file_path)
    return file_paths

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Lint files.')
    parser.add_argument('--recursive', '-r', action='store_true', help='lint files recursively')
    parser.add_argument('filenames', nargs='+', help='file(s) to lint')
    args = parser.parse_args()

    if args.recursive:
        filenames = []
        for directory in args.filenames:
            filenames.extend(get_files_recursively(directory))
        args.filenames = filenames

    main(args.filenames)
