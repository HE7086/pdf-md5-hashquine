# pdf-md5-hashquine

A PDF that shows its own MD5

* [Background](#background)
  * [Merkle–Damgård construction](#merkle–damgård-construction)
  * [jpeg markers](#jpeg-markers)
  * [unicoll](#unicoll)
* [Exploit](#exploit)
  * [structure of the pdf](#structure-of-the-pdf)
  * [structure of the jpg](#structure-of-the-jpg)
    * [a closer look at collision block](#a-closer-look-at-collision-block)
* [Usage](#usage)
  * [project structure](#project-structure)
  * [requirements](#requirements)
  * [Script Usage](#script-usage)
    * [generate the data](#generate-the-data)
    * [observe while running](#observe-while-running)
    * [combine the data](#combine-the-data)
  * [Example PDF File](#example-pdf-file)
* [Reference](#reference)

## Background

### [Merkle–Damgård construction](https://en.wikipedia.org/wiki/Merkle%E2%80%93Damg%C3%A5rd_construction)

MD5 is designed with this specific construction, which means:

* consider A, B, C, D as blocks with size of `N * 64` bytes
    - if `md5(A) == md5(B)`, then `md5(A || C) == md5(B || C)`
    - furthermore, if `md5(A || C) == md5(A || D)`, then 
      - `md5(A || C) == md5(B || C)`
      - `md5(A || C) == md5(B || D)`
      - `md5(A || D) == md5(B || C)`
      - `md5(A || D) == md5(B || D)`
    - however, this does not necessarily mean  
    if `md5(A) == md5(B)`, then `md5(C || A) == md5(C || B)`  
    => prefix can influence the collisions!

with these properties, we are able to generate `2^N` files with same md5 with `N` collision blocks.

### [jpeg markers](https://en.wikipedia.org/wiki/JPEG)

the common image format jpeg supports comment blocks with variable size, in particular:

* a comment block in jpeg should start with the byte `FFFE`, then followed by 2 bytes of comment length (including the length mark itself) in big endian, and then comment data.  
for example, a regular comment block looks like this:
```
FFFE 000E 0000 0000 0000 0000 0000 0000
```

we can manipulate the comment block to hide some information inside it.

### [unicoll](https://github.com/cr-marcstevens/hashclash)

hashclash provides us with a very convenient way to generate collision blocks, namely unicoll

* using a prefix of `N * 64` + `M * 4` bytes, unicoll will generate a pair of collision, and the 10th byte of the collision blocks is guaranteed to have a diff of 1.  
the collision block is also guaranteed to be 128 bytes long.  
 
for example:

```
                                || diff byte
collision block 1               \/
00000000: 0000 0000 0000 00ff fe00 7700 b3e3 69c4  ..........w...i.
00000010: b143 ae27 d9da f3c0 bc0b 6c21 4bb0 46d1  .C.'......l!K.F.
00000020: 7e85 fbde 58a6 b1e0 7ab6 14e4 0065 a684  ~...X...z....e..
00000030: 8aaf 6865 e4e6 9a44 cedf c6f2 77ce 3adc  ..he...D....w.:.
00000040: c4e2 4654 fd32 4875 ecb5 b741 23b7 164d  ..FT.2Hu...A#..M
00000050: e0b4 7c3d 705c 276a 0151 7880 83c7 5e22  ..|=p\'j.Qx...^"
00000060: 02d2 bcdb d39c 83e2 ba5f 3e03 ae6e b780  ........._>..n..
00000070: 996a 9f3a d163 5773 57af 4bcf a6df cc72  .j.:.cWsW.K....r

                                || diff byte
collision block 2               \/
00000000: 0000 0000 0000 00ff fe01 7700 b3e3 69c4  ..........w...i.
00000010: b143 ae27 d9da f3c0 bc0b 6c21 4bb0 46d1  .C.'......l!K.F.
00000020: 7e85 fbde 58a6 b1e0 7ab6 14e4 0065 a684  ~...X...z....e..
00000030: 8aaf 6865 e4e6 9a44 cedf c6f2 77ce 3adc  ..he...D....w.:.
00000040: c4e2 4654 fd32 4875 ecb4 b741 23b7 164d  ..FT.2Hu...A#..M
00000050: e0b4 7c3d 705c 276a 0151 7880 83c7 5e22  ..|=p\'j.Qx...^"
00000060: 02d2 bcdb d39c 83e2 ba5f 3e03 ae6e b780  ........._>..n..
00000070: 996a 9f3a d163 5773 57af 4bcf a6df cc72  .j.:.cWsW.K....r
```
the above two block was generated using prefix `0000 0000 0000 00ff fe00 7700`  
they have the same md5 value, and have a diff on the 10th byte of 1

according to the doc of hashclash, M must be less than 4 (which means you can control up to 12 bytes in the collision block), my test shows however, 20 bytes also work with hashclash, it's only a bit slower.

## Exploit

We can make use of the above properties to generate jpgs that have same md5 and then replace them in the pdf without influencing the md5 of it. (of course the collision block inside jpg has to be aligned)

### structure of the pdf

the md5 is splitted into 32 digits, and each one of them is displayed by a jpg

| structure         |
|-------------------|
| PDF Header        |
| **object prefix** |
| **image**         |
| **object suffix** |
| ... (32x)         |
| PDF Trailer       |

the bold part is repeated 32 times for 32 digits of md5  
note that we have to specify 32 different images in the latex source to prevent referencing

### structure of the jpg

| structure           |
|---------------------|
| JPG prefix          |
| **collision block** |
| **image data**      |
| ... (16x)           |
| JPG suffix          |

If all the image shares the same Exif, huffman/quantization table, they can be put in the jpg prefix. This increases compatibility since some of the image viewer do not expect comment block at the beginning of the image.  

the bold part is repeated 16 times for 16 hex numbers  

#### a closer look at collision block

* example collision block
```
                      ||---------------- when this lenth is 0x0077,
0000 0000 0000 00ff fe00 7700 b3e3 69c4  the comment block lasts till padding.
b143 ae27 d9da f3c0 bc0b 6c21 4bb0 46d1  when it's 0x0177, 
7e85 fbde 58a6 b1e0 7ab6 14e4 0065 a684  the padding block is also included
8aaf 6865 e4e6 9a44 cedf c6f2 77ce 3adc  inside this comment block
c4e2 4654 fd32 4875 ecb5 b741 23b7 164d  and the next block is then data of image
e0b4 7c3d 705c 276a 0151 7880 83c7 5e22
02d2 bcdb d39c 83e2 ba5f 3e03 ae6e b780
996a 9f3a d163 5773 57af 4bcf a6df cc72
```

* padding (256 bytes)
```
|---- 0x0077 goes till here
|    |--|------------------------------- length of the comment block + image
FFFE 0F45 0000 0000 0000 0000 0000 0000  if this comment is read, the following image
0000 0000 0000 0000 0000 0000 0000 0000  will also be ignored.
0000 0000 0000 0000 0000 0000 0000 0000  this length should be determined by your image
0000 0000 0000 0000 0000 0000 0000 0000
.... (padding)
```

* image data
```
|---- 0x0177 goes till here
FFDA .... (image data)
# start of scan mark
```

## Usage

### project structure
```
/
  bin/                 # hashclash binaries
  scripts/             # hashclash scripts
  project/             # project folder
    binary/            # prepared binary data
      digits/
        prefix.bin     # prefix of the image, including exif etc.
        suffix.bin     # suffix of the image, with some padding
        *.bin          # body part of the image
      pdf/
        pdfHeader.bin  # header of pdf
        pdfTrailer.bin # trailer of pdf
        obj_start.bin  # object prefix
        obj_end.bin    # object suffix
      originalJPG/
        *.jpg          # original jpg files before splitting
    tex/               # latex sources
    combine.py         # script to combine the data into pdf
    gen.py             # script to generate data
    jpg.py             # script to generate jpg (not necessary for pdf)
```

### requirements
* [hashclash](https://github.com/cr-marcstevens/hashclash/releases/download/hashclash-static-release-v1.2b/hashclash-static-release-v1.2b.tar.gz)  
note that the `bin` and `scripts` folder must exactly located as above (on the same level of project) otherwise it will fail to read prefix for some reason
* python3.8+  
(can be adapted to 3.7 by removing `:=` operator)
* unix shell environment  
(for command like `killall` to work)

### Script Usage
#### generate the data
```
cd project
./gen.py
```
This might take tens of hours to find collisions (we need 32*16=512 of them). On a ryzen5 3600 it took about 24 hours.  
you may need to increase the timeout in the subprocess run if your cpu is less powerful  
hashclash may get stuck on some certain diffpath for hours so I set a timeout of 200 seconds. If no collision is found in 200s, it will kill the script and restart current step  

If the script is interrupted, you can continue it using `./gen.py <current index>` without restarting from the very beginning.

#### observe while running
```
watch tail -n 40 ./logs/log.txt
```
This will show you which step we are currently at and whether there's timeout.

#### combine the data
```
./combine.py
```
The script will combine the calculated data into one pdf file, located at `./output.pdf`

### Example PDF File
see [release](https://github.com/HE7086/pdf-md5-hashquine/releases)

## Reference
* [hashclash](https://github.com/cr-marcstevens/hashclash)
* [collisions](https://github.com/corkami/collisions)
* [PoC||GTFO 14](https://github.com/angea/pocorgtfo#0x14)
