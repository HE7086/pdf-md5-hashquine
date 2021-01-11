#!/usr/bin/env python3

with open('md5.pdf', 'rb') as f:
    
    data = f.read(418)
    with open('pdfHeader.bin', 'wb') as h:
        h.write(data)

    data = f.read(149)
    with open('obj_start.bin', 'wb') as h:
        h.write(data)

    f.read(65280)

    data = f.read(18)
    with open('obj_end.bin', 'wb') as h:
        h.write(data)

    data = f.read()
    with open('pdfTrailer.bin', 'wb') as h:
        h.write(data[-19797:])


