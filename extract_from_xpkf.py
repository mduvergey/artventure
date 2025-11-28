#!/usr/bin/env python3

import argparse
from PIL import Image, ImagePalette


# Based on code from https://github.com/temisu/ancient
def unpack_nuke(packed_data, unpacked_size):
    input_offset = len(packed_data)

    output_data = bytearray(unpacked_size)
    output_offset = 0

    bit_stream_offset = 0

    bit_1_reader_count = 0
    bit_1_reader_data = 0

    bit_2_reader_count = 0
    bit_2_reader_data = 0

    bit_4_reader_count = 0
    bit_4_reader_data = 0

    bit_x_reader_count = 0
    bit_x_reader_data = 0

    vlc_values = (4, 6, 8, 9, -4, 7, 9, 11, 13, 14, -5, 7, 9, 11, 13, 14)
    vlc_offsets = []
    vlc_bit_lengths = []
    length = 0
    for v in vlc_values:
        vlc_bit_lengths.append(abs(v))
        if v < 0:
            vlc_offsets.append(0)
            length = 1 << -v
        else:
            vlc_offsets.append(length)
            length += 1 << v

    def read_bits_generic_msb(count, reader_count, reader_data):
        nonlocal bit_stream_offset
        ret = 0
        while count > 0:
            if reader_count == 0:
                reader_data = int.from_bytes(packed_data[bit_stream_offset:bit_stream_offset + 2])
                reader_count = 16
                bit_stream_offset += 2
            max_count = min(reader_count, count)
            reader_count -= max_count
            ret = ret << max_count | (reader_data >> reader_count) & ((1 << max_count) - 1)
            count -= max_count
        return ret, reader_count, reader_data

    def read_x_bits_msb(count):
        nonlocal bit_x_reader_count, bit_x_reader_data
        ret, bit_x_reader_count, bit_x_reader_data = read_bits_generic_msb(count, bit_x_reader_count, bit_x_reader_data)
        return ret

    def read_bit_msb():
        nonlocal bit_1_reader_count, bit_1_reader_data
        ret, bit_1_reader_count, bit_1_reader_data = read_bits_generic_msb(1, bit_1_reader_count, bit_1_reader_data)
        return ret

    def read_2_bits_msb():
        nonlocal bit_2_reader_count, bit_2_reader_data
        ret, bit_2_reader_count, bit_2_reader_data = read_bits_generic_msb(2, bit_2_reader_count, bit_2_reader_data)
        return ret

    def read_4_bits_lsb():
        nonlocal bit_4_reader_count, bit_4_reader_data, bit_stream_offset
        ret = 0
        pos = 0
        count = 4
        while count > 0:
            if bit_4_reader_count == 0:
                bit_4_reader_data = int.from_bytes(packed_data[bit_stream_offset:bit_stream_offset + 4])
                bit_4_reader_count = 32
                bit_stream_offset += 4
            max_count = min(bit_4_reader_count, count)
            ret |= (bit_4_reader_data & ((1 << max_count) - 1)) << pos
            bit_4_reader_data >>= max_count
            bit_4_reader_count -= max_count
            count -= max_count
            pos += max_count
        return ret

    while True:
        if read_bit_msb() == 0:
            count = 0
            if read_bit_msb() != 0:
                count = 1
            else:
                while True:
                    tmp = read_2_bits_msb()
                    if tmp != 0:
                        count += 5 - tmp
                    else:
                        count += 3
                    if tmp != 0:
                        break
            for _ in range(count):
                input_offset -= 1
                output_data[output_offset] = packed_data[input_offset]
                output_offset += 1

        if output_offset >= unpacked_size:
            break

        distance_index = read_4_bits_lsb()
        distance = vlc_offsets[distance_index] + read_x_bits_msb(vlc_bit_lengths[distance_index])
        if distance_index < 4:
            count = 2
        elif distance_index < 10:
            count = 3
        else:
            count = 0

        if count == 0:
            count = read_2_bits_msb()
            if count == 0:
                count = 3 + 3
                while True:
                    tmp = read_4_bits_lsb()
                    if tmp != 0:
                        count += 16 - tmp
                    else:
                        count += 15
                    if tmp != 0:
                        break
            else:
                count = 3 + 4 - count

        for i in range(count):
            output_data[output_offset + i] = output_data[output_offset - distance + i]
        output_offset += count

    return output_data


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

    if args.verbose:
        print(f'Image info: {width} x {height}, {bitplanes} bitplanes ({2 << bitplanes - 1} colors)')

    pcrc_chunk_offset = image_file_data.find(bytes('PCRC', 'utf-8'), 16)

    if pcrc_chunk_offset != 16:
        print('Unable to find PCRC chunk. Aborting.')
        exit(3)

    if args.verbose:
        print('Found PCRC chunk.')

    color_count = int.from_bytes(image_file_data[20:24]) // 3

    if args.verbose:
        print(f'Palette size: {color_count} entries')

    image = bytearray(width * height)
    plane_number = 0
    xpkf_chunk_offset = image_file_data.find(bytes('XPKF', 'utf-8'))

    while xpkf_chunk_offset >= 0:
        packed_size = int.from_bytes(image_file_data[xpkf_chunk_offset + 36 + 4:xpkf_chunk_offset + 36 + 6])
        raw_size = int.from_bytes(image_file_data[xpkf_chunk_offset + 36 + 6:xpkf_chunk_offset + 36 + 8])

        packed_chunk_type = image_file_data[xpkf_chunk_offset + 36]
        if packed_chunk_type == 0:
            unpacked_data = image_file_data[xpkf_chunk_offset + 36 + 8:xpkf_chunk_offset + 36 + 8 + packed_size]
        elif packed_chunk_type == 1:
            unpacked_data = unpack_nuke(image_file_data[xpkf_chunk_offset + 36 + 8:xpkf_chunk_offset + 36 + 8 + packed_size], raw_size)

        bit_count = 0
        offset = 0
        for i in range(height):
            for j in range(width):
                if bit_count == 0:
                    bit_data = unpacked_data[offset]
                    bit_count = 8
                    offset += 1
                bit_count -= 1
                bit = bit_data >> bit_count & 1
                image[i * width + j] = image[i * width + j] | bit << plane_number

        xpkf_chunk_offset = image_file_data.find(bytes('XPKF', 'utf-8'), xpkf_chunk_offset + 4)
        plane_number += 1

    img = Image.frombytes('P', (width, height), image)
    img.putpalette(ImagePalette.ImagePalette('RGB', image_file_data[24:24 + color_count * 3]))
    img.save(args.filename + '.png')

    if args.verbose:
        print(f'Image saved to file {args.filename + '.png'}.')

    print('Done.')

except FileNotFoundError:
    print(f'Could not open file {args.filename}.')
    exit(1)
