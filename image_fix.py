#!/usr/bin/env python3

import argparse

parser = argparse.ArgumentParser(description='Fixes IFF/ILBM header of image files from Artventure games')
parser.add_argument('filename')
parser.add_argument('-g', '--game', default='holiday', help='tells the program which game the image comes from', choices=('holiday', 'loewen'))
parser.add_argument('-o', '--output', help='name of file to write the fixed image to')
parser.add_argument('-v', '--verbose', help='prints extra information about image', action='store_true')

args = parser.parse_args()

games = {
    'holiday': 'Holiday Maker',
    'loewen': 'Die Stadt der Loewen'
}

if args.verbose:
    print(f'Selected game: {games[args.game]}')

try:
    input_file = open(args.filename, 'rb')
    image_file_data = input_file.read()

    bitmap_header_offset = image_file_data.find(bytes('BMHD', 'utf-8'))

    if bitmap_header_offset < 0:
        print('Unable to locate bitmap header (BMHD). File is not an IFF/ILBM file?')
        exit(2)

    if args.verbose:
        width = int.from_bytes(image_file_data[bitmap_header_offset + 8:bitmap_header_offset + 10])
        height = int.from_bytes(image_file_data[bitmap_header_offset + 10:bitmap_header_offset + 12])
        bitplane_count = image_file_data[bitmap_header_offset + 16]
        compression_type = image_file_data[bitmap_header_offset + 18]
        print(f'Image dimensions: {width} x {height}')
        print(f'Bitplane count: {bitplane_count}')
        print(f'Compression type: {compression_type}')

        body_offset = image_file_data.find(bytes('BODY', 'utf-8'))
        body_size = int.from_bytes(image_file_data[body_offset + 4:body_offset + 8])
        print(f'BODY part size: {body_size}')

    needs_patching = False

    # Holiday Maker
    if args.game == 'holiday':
        print('Checking FORM marker...')
        needs_patching |= image_file_data[2] != ord('R')
        print('Checking ILBM marker...')
        needs_patching |= image_file_data[10] != ord('B')

    # Die Stadt der Loewen
    elif args.game == 'loewen':
        print('Checking compression type...')
        needs_patching |= image_file_data[bitmap_header_offset + 18] != 1

    if needs_patching:
        print('Image file needs to be patched.')
        if not args.output:
            print('Use -o option to specify an output file.')
    else:
        print('Image file does not require patching.')
        exit(3)

    if args.output:
        writeable_array = bytearray(image_file_data)

        # Holiday Maker
        if args.game == 'holiday':
            writeable_array[2] = ord('R')
            writeable_array[10] = ord('B')

        # Die Stadt der Loewen
        elif args.game == 'loewen':
            writeable_array[bitmap_header_offset + 18] = 1

        try:
            patched_file = open(args.output, 'xb')
            patched_file.write(writeable_array)
            if args.verbose:
                print(f'Patched image has been written to {args.output}.')

        except FileExistsError:
            print(f'File {args.output} already exists. Aborting.')
            exit(4)

except FileNotFoundError:
    print(f'Could not open file {args.filename}.')
    exit(1)
