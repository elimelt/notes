import argparse
import subprocess

def replace_chars(input_files, backup):
    # characters to replace
    replacements = {
        '—': '-',
        '–': '-',
        "’": "'",
        '”': '"',
        '“': '"',
        '…': '...'
    }

    # generate sed script
    sed_script = []
    for old_char, new_char in replacements.items():
        sed_script.append(f"s/{old_char}/{new_char}/g")

    # write to tpm file
    sed_file_path = 'sed_commands.tpm'
    with open(sed_file_path, 'w') as f:
        f.write('\n'.join(sed_script))

    # Perform replacements on each input file
    for input_file in input_files:
        output_file = f"{input_file}.tmp"
        if backup:
            # backup original file
            subprocess.run(['cp', input_file, f"{input_file}.bak"])

        # replacements with sed
        subprocess.run(['sed', '-f', sed_file_path, input_file], stdout=open(output_file, 'w'))

        # replace orginal file
        subprocess.run(['mv', output_file, input_file])

    # cleanup
    subprocess.run(['rm', sed_file_path])

    print("Replacement done.")


# run with -b to create backup files
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Character replacement utility")
    parser.add_argument('input_files', nargs='+', help='List of input files')
    parser.add_argument('-b', '--backup', action='store_true', help='Create backup of original files')

    args = parser.parse_args()

    replace_chars(args.input_files, args.backup)
