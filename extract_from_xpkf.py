#!/usr/bin/env python3

import argparse

parser = argparse.ArgumentParser(description='Extract images from Jonathan (Amiga) XPKF-compressed files')
parser.add_argument('filename')
parser.add_argument('-v', '--verbose', help='prints extra information about image', action='store_true')

args = parser.parse_args()

try:
    input_file = open(args.filename, 'rb')
    image_file_data = input_file.read()
    input_file.close()

    pcrh_chunk_offset = image_file_data.find(bytes('PCRH', 'utf-8'))

    if pcrh_chunk_offset != 0:
        print('Unable to find PCRH chunk. Aborting.')
        exit(2)

    if args.verbose:
        print('Found PCRH chunk.')
        width = int.from_bytes(image_file_data[8:10])
        height = int.from_bytes(image_file_data[10:12])
        bitplanes = int.from_bytes(image_file_data[15:16])
        print(f'Image info: {width} x {height}, {bitplanes} bitplanes ({2 << bitplanes - 1} colors)')

    pcrc_chunk_offset = image_file_data.find(bytes('PCRC', 'utf-8'), 16)

    if pcrc_chunk_offset != 16:
        print('Unable to find PCRC chunk. Aborting.')
        exit(3)

    if args.verbose:
        print('Found PCRC chunk.')
        color_count = int.from_bytes(image_file_data[20:24]) // 3
        print(f'Palette size: {color_count} entries')

    chunk_number = 1
    xpkf_chunk_offset = image_file_data.find(bytes('XPKF', 'utf-8'))
    while xpkf_chunk_offset >= 0:
        start_offset = xpkf_chunk_offset
        xpkf_chunk_len = int.from_bytes(image_file_data[xpkf_chunk_offset+4:xpkf_chunk_offset+8])
        # print('XPKF chunk length = ' + str(xpkf_chunk_len))
        nuke_chunk_uncompressed_len = int.from_bytes(image_file_data[xpkf_chunk_offset+12:xpkf_chunk_offset+16])
        # print('NUKE chunk uncompressed length = ' + str(nuke_chunk_uncompressed_len))
        xpkf_chunk_offset = image_file_data.find(bytes('XPKF', 'utf-8'), xpkf_chunk_offset + 4)
        if xpkf_chunk_offset >= 0:
            end_offset = xpkf_chunk_offset
        else:
            end_offset = len(image_file_data)
        # output_file = open(f'{args.filename}.part.{chunk_number}', 'xb')
        # output_file.write(image_file_data[start_offset:end_offset])
        # output_file.close()
        chunk_number += 1


except FileNotFoundError:
    print(f'Could not open file {args.filename}.')
    exit(1)
