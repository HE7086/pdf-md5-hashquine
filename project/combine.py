#!/usr/bin/env python3

from binascii import hexlify
import hashlib
import os


def md5(data: bytes) -> str:
    return hexlify(hashlib.md5(data).digest()).decode()


def main() -> None:
    # check if the data is generated
    if not os.path.exists('31_data.bin'):
        print('collision data not found')
        exit(1)

    # prepare the data of target pdf
    with open('31_data.bin', 'rb') as f:
        data: bytes = f.read()
    with open('binary/pdf/pdfTrailer.bin', 'rb') as f:
        trailer: bytes = f.read()
    # update the address to the xref table
    trailer = trailer[:-14]
    data += trailer
    xref_index: int = -1
    for i in reversed(range(len(data))):
        if data[i: i + 21] == b' 0 obj\n<<\n/Type /XRef':
            for j in range(16):
                if data[i - j] == 0x0a:  # find last '\n'
                    xref_index = i - j + 1
                    break
            else:
                continue
            break
    assert xref_index > 0
    trailer += str(xref_index).encode()
    trailer += b'\n%%EOF\n'
    data += str(xref_index).encode()
    data += b'\n%%EOF\n'

    # calculate md5 of target pdf
    md5_src: str = md5(data)
    print(f'target md5:    {md5_src}')

    # generate the pdf from collision
    pdf: bytes = b''
    with open('binary/pdf/pdfHeader.bin', 'rb') as f:
        pdf += f.read()
    # insert the specific image with generated collision
    for i in range(len(md5_src)):
        with open(f'./{i}_{md5_src[i]}.bin', 'rb') as f:
            pdf += f.read()
    pdf += trailer
    md5_pdf: str = md5(pdf)
    print(f'generated md5: {md5_pdf}')
    assert(md5_pdf == md5_src)

    with open('./output.pdf', 'wb') as f:
        f.write(pdf)


if __name__ == '__main__':
    main()
