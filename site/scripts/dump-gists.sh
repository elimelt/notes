
base=$1

if [ -z "$base" ]; then
  echo "Usage: $0 <directory>"
  exit 1
fi

if [ ! -d "$base" ]; then
  echo "Directory $base does not exist. Creating it."
  mkdir -p "$base"
fi

# go line by line
lines=$(gh gist list -L 10000)
echo "$lines" | while read -r line; do
  id=$(echo $line | awk '{print $1}')
  file_name=$(echo $line | awk '{print $2}')
  echo "Fetching gist $id with file name $file_name"
  gh gist view $id --raw > "$base/$file_name"
done
