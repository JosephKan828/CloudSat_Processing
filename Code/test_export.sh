era5_file="my_test_file"
seq 1 1 | xargs -n 1 bash -c 'echo "1: $era5_file"' _ 2006
export era5_file
seq 1 1 | xargs -n 1 bash -c 'echo "2: $era5_file"' _ 2006
