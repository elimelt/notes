import subprocess

def replace_chars(input_file):
    replacements = {
        '—': '-'
    }

    sed_script = []
    for old_char, new_char in replacements.items():
        sed_script.append(f"s/{old_char}/{new_char}/g")

    sed_file_path = 'sed_commands.txt'
    with open(sed_file_path, 'w') as f:
        f.write('\n'.join(sed_script))

    output_file = f"{input_file}_modified"
    subprocess.run(['sed', '-f', sed_file_path, input_file], stdout=open(output_file, 'w'))

    subprocess.run(['rm', sed_file_path])

    print(f"Replacement done. Modified file is {output_file}.")

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python script_name.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    replace_chars(input_file)
