#!/usr/bin/env python3

from datetime import datetime
import os
import subprocess
import sys
from time import sleep


# write log message with time
def write_log(msg: str) -> None:
    with open('./logs/log.txt', 'a') as logger:
        msg = f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  {msg}\n'
        logger.write(msg)
        print(msg, file=sys.stderr)


# get the image size and its padding size
def get_image_size_and_padding(file: str) -> tuple[int, int]:
    image_data_size: int = os.path.getsize(file)
    if image_data_size % 64 == 0:
        image_padding_size: int = 64
    elif image_data_size % 64 < 4:
        # not enough for comment block
        image_padding_size: int = 64 + 64 - image_data_size % 64
    else:
        image_padding_size: int = 64 - image_data_size % 64
    return image_data_size, image_padding_size


class UniCollError(Exception):
    pass


# get the collision block for given file
def unicoll(prefix: str) -> tuple[bytes, bytes]:
    # make sure the file is correctly padded
    with open(prefix, 'rb') as f:
        data: bytes = f.read()
        assert len(data) % 64 == 12
        assert data[-5:] == b'\xff\xfe\x00\x77\x00'
        # store the data in case of timeout
        data = data[:-12]

    # 5 retries
    for _ in range(5):
        try:
            # timeout of 200 seconds
            subprocess.run(['../scripts/poc_no.sh', prefix], timeout=200)

        except subprocess.TimeoutExpired:
            # kill zombie processes
            os.system('killall -r "md5_diff.*"')
            write_log('***Time Out***')
            with open(prefix, 'wb') as f:
                f.write(data)
                # random bytes to prevent timeout
                f.write(os.getrandom(7))
                f.write(b'\xff\xfe\x00\x77\x00')
            sleep(1)
            continue

        else:
            os.system('killall -r "md5_diff.*"')
            write_log('OK')
            # collision with 0x0077
            with open('collision1.bin', 'rb') as f:
                c0: bytes = f.read()[-128:]
                assert c0[9:11] == b'\x00\x77'
            # collision with 0x0177
            with open('collision2.bin', 'rb') as f:
                c1: bytes = f.read()[-128:]
                assert c1[9:11] == b'\x01\x77'
            os.remove('collision1.bin')
            os.remove('collision2.bin')
            return c0, c1

    # after 5 retries still no success -> retry current run
    raise UniCollError('too many retries, aborting')


def run(index: int) -> None:
    data: bytearray = bytearray()
    if index == 0:
        with open('./init_data.bin', 'rb') as f:
            data += f.read()
    else:
        # use the data from previous run
        with open(f'./{index - 1}_data.bin', 'rb') as f:
            data += f.read()

    obj_index: int = len(data)
    # common headers
    with open('./binary/pdf/obj_start.bin', 'rb') as f:
        data += str(index + 1).encode()  # index of the object
        data += f.read(91)[1:]
        length_index = len(data)
        data += str(65280).encode()  # length of image, place holder
        data += f.read()[5:]

    image_index: int = len(data)
    # image header
    with open('./binary/digits/prefix.bin', 'rb') as f:
        data += f.read()

    # padding
    if (length := len(data)) % 64 != 0:
        # if the remainder is not enough for a comment block
        if (l := 64 - length % 64) < 4:
            data += b'\xff\xfe'
            # block size - space for 0xfffe + remain size
            # + additional padding for collision
            data += (64 - 2 + l + 7).to_bytes(2, 'big')
            data += b'\x00' * (64 - l - 4)
        else:
            data += b'\xff\xfe'
            data += (l - 2).to_bytes(2, 'big')
            data += b'\x00' * (l - 4)
            # additional padding for collision
            data += b'\xff\xfe'
            data += (64 - 2 + 7).to_bytes(2, 'big')
            data += b'\x00' * (64 - 4)
    else:
        # additional padding for collision
        data += b'\xff\xfe'
        data += (64 - 2 + 7).to_bytes(2, 'big')
        data += b'\x00' * 60

    image_size: int = len(data) - image_index
    for digit in range(16):
        image_data_size, image_padding_size = get_image_size_and_padding(f'./binary/digits/{digit:x}.bin')
        # (collision + padding + image data size + padding) * 16
        image_size += 128 + 256 + image_data_size + image_padding_size
    # precalculated suffix
    image_size += 64
    # fill the place holder with the actual image size
    data[length_index: length_index + 5] = str(image_size).encode()

    # create storage for results
    for digit in range(16):
        with open(f'./{index}_{digit:x}.bin', 'wb') as f:
            f.write(data[obj_index:])
    with open(f'./{index}_data.bin', 'wb') as f:
        f.write(data)

    # start calculation
    for digit in range(16):
        with open(f'./{index}_data.bin', 'ab') as f:
            # comment block for collision
            f.write(b'\x00' * 7)
            f.write(b'\xff\xfe\x00\x77\x00')

        write_log(f'{index} {digit}')
        c0, c1 = unicoll(f'./{index}_data.bin')

        # update the storage
        data = bytearray()
        # padding to next image
        data += b'\xff\xfe'
        image_data_size, image_padding_size = get_image_size_and_padding(f'./binary/digits/{digit:x}.bin')
        data += (256 - 2 + image_data_size + image_padding_size + 7).to_bytes(2, 'big')
        data += b'\x00' * (256 - 4)
        # image data
        with open(f'./binary/digits/{digit:x}.bin', 'rb') as f:
            data += f.read()
        # padding to next image
        data += b'\xff\xfe'
        data += (image_padding_size - 2 + 7).to_bytes(2, 'big')
        data += b'\x00' * (image_padding_size - 4)
        for i in range(16):
            with open(f'./{index}_{i:x}.bin', 'ab') as f:
                if i == digit:
                    f.write(c1)  # show
                else:
                    f.write(c0)  # hide
                f.write(data)

        # remove the redundant comment block
        with open(f'./{index}_data.bin', 'rb+') as f:
            f.seek(-12, os.SEEK_END)
            f.truncate()
        with open(f'./{index}_data.bin', 'ab') as f:
            f.write(c0)  # either c0 or c1 is fine here
            f.write(data)

        assert os.path.getsize(f'./{index}_data.bin') % 64 == 0

    # all digits are calculated, append the suffix
    with open('./binary/digits/suffix.bin', 'rb') as g:
        suffix: bytes = g.read()
    with open('./binary/pdf/obj_end.bin', 'rb') as g:
        suffix += g.read()
    for i in range(16):
        with open(f'./{index}_{i:x}.bin', 'ab') as f:
            f.write(suffix)
    with open(f'./{index}_data.bin', 'ab') as f:
        f.write(suffix)


def main():
    # control which index to start with of the whole file
    if len(sys.argv) > 1:
        index = int(sys.argv[1])
    else:
        index = 0
        # initialization
        with open('./binary/pdf/pdfHeader.bin', 'rb') as f:
            data = f.read()
        with open('./init_data.bin', 'wb') as f:
            f.write(data)
    # calculate on each index
    for i in range(index, 32):
        while True:
            try:
                run(i)
            except UniCollError:
                write_log('unicoll failed')
                os.remove(f'{i}_data.bin')
                for j in range(16):
                    os.remove(f'{i}_{j:x}.bin')
            else:
                break


if __name__ == '__main__':
    main()
