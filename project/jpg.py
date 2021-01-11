#!/usr/bin/env python3
def main():
    for i in range(32):
        for j in range(16):
            with open(f'{i}_{j:x}.bin', 'rb') as f:
                data = f.read()
            for k in range(len(data)):
                if data[k: k + 4] == b'\xff\xd8\xff\xe0':
                    data = data[k: -18]
            with open(f'./tex/digits/{i}_{j:x}.jpg', 'wb') as f:
                f.write(data)


if __name__ == '__main__':
    main()
