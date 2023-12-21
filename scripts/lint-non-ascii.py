import sys

def lint_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        line_number = 0
        for line in f:
            line_number += 1
            for char in line:
                if ord(char) > 127:  # ASCII range is 0-127
                    # print line number and character in green
                    print(f"Line \033[92m{line_number}\033[0m: \033[92m{char}\033[0m")

def main(filenames):
    for filename in filenames:
        # print filename in red
        print(f"Linting \033[91m{filename}\033[0m")
        lint_file(filename)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python linter.py <file1> <file2> ...")
        sys.exit(1)

    main(sys.argv[1:])
