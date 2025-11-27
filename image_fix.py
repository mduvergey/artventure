#!/usr/bin/env python3

import argparse

parser = argparse.ArgumentParser(description='Fixes header of image files from Artventure Amiga/PC games')
parser.add_argument('-g', '--game', help='tells the program which game the image comes from', choices=('holiday', 'loewen', 'jonpc'))
parser.add_argument('-i', '--input', help='name of image file to fix')
parser.add_argument('-o', '--output', help='name of file to write the fixed image to')
parser.add_argument('-lg', '--list-games', help='lists supported games', action='store_true')
parser.add_argument('-v', '--verbose', help='prints extra information about image', action='store_true')

args = parser.parse_args()

games = {
    'holiday': 'Holiday Maker',
    'loewen': 'Die Stadt der Loewen',
    'jonpc': 'Jonathan (PC)'
}

if args.list_games:
    print('Supported games:')
    for key in games:
        print(f'- {games[key]} ({key})')
    exit()

if args.verbose:
    print(f'Selected game: {games[args.game]}')

if args.input is None:
    print('Missing input filename. Use -i option.')
    exit(1)

try:
    input_file = open(args.input, 'rb')
    image_file_data = input_file.read()
    input_file.close()

    if args.game in ('holiday', 'loewen'):
        bitmap_header_offset = image_file_data.find(bytes('BMHD', 'utf-8'))

        if bitmap_header_offset < 0:
            print('Unable to locate bitmap header (BMHD). File is not an IFF/ILBM file?')
            exit(3)

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

    elif args.game == 'jonpc':
        if args.verbose:
            x_min = int.from_bytes(image_file_data[4:6], 'little')
            y_min = int.from_bytes(image_file_data[6:8], 'little')
            x_max = int.from_bytes(image_file_data[8:10], 'little')
            y_max = int.from_bytes(image_file_data[10:12], 'little')
            print(f'Image rect: ({x_min}, {y_min}) -> ({x_max, y_max})')

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

    # Jonathan (PC)
    elif args.game == 'jonpc':
        print('Checking PCX header...')
        needs_patching |= image_file_data[0] == 0 and image_file_data[1] == 0 and image_file_data[2] == 0 and image_file_data[3] == 0

    if needs_patching:
        print('Image file needs to be patched.')
        if args.output is None:
            print('Use -o option to specify an output file.')
            exit(4)
    else:
        print('Image file does not require patching.')
        exit(5)

    writeable_array = bytearray(image_file_data)

    # Holiday Maker
    if args.game == 'holiday':
        writeable_array[2] = ord('R')
        writeable_array[10] = ord('B')

    # Die Stadt der Loewen
    elif args.game == 'loewen':
        writeable_array[bitmap_header_offset + 18] = 1

    # Jonathan (PC)
    elif args.game == 'jonpc':
        writeable_array[0] = 0x0A
        writeable_array[1] = 5
        writeable_array[2] = 1
        writeable_array[3] = 8

    try:
        patched_file = open(args.output, 'xb')
        patched_file.write(writeable_array)
        patched_file.close()

        if args.verbose:
            print(f'Patched image has been written to {args.output}.')

    except FileExistsError:
        print(f'File {args.output} already exists. Aborting.')
        exit(6)

    print('Done.')

except FileNotFoundError:
    print(f'Could not open file {args.input}.')
    exit(2)
