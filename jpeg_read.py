#!/usr/bin/env python

import sys
import copy
from math import *
from Tkinter import *

huffman_ac_tables= [{}, {}, {}, {}]
huffman_dc_tables= [{}, {}, {}, {}]

q_table= [[], [], [], []]

XYP= 0, 0, 0
component= {}
num_components= 0
mcus_read= 0
dc= []
inline_dc= 0

idct_precision= 8

EOI= False
data= []


def read_word(file):
   out= ord(file.read(1)) << 8
   out|= ord(file.read(1))

   return out

def read_byte(file):
   out= ord(file.read(1))

   return out


def read_dht(file):
   global huffman_ac_tables
   global huffman_dc_tables

   Lh= read_word(file)
   Lh-= 2
   while Lh>0:
      huffsize= []
      huffval= []
      print "Lh: %d" % Lh
      T= read_byte(file)
      Th= T & 0x0F
      print "Th: %d" % Th
      Tc= (T >> 4) & 0x0F
      print "Tc: %d" % Tc
      Lh= Lh-1

      for i in range(16):
         huffsize.append(read_byte(file))
         Lh-= 1

      huffcode= huffman_codes(huffsize)

      print "Huffcode", huffcode

      for i in huffcode:
         huffval.append(read_byte(file))
         Lh-= 1

      if Tc==0:
         huffman_dc_tables[Th]= map_codes_to_values(huffcode, huffval)
      else:
         huffman_ac_tables[Th]= map_codes_to_values(huffcode, huffval)


def map_codes_to_values(codes, values):
   out= {}

   for i in range(len(codes)):
      out[codes[i]]= values[i]

   return out


def huffman_codes(huffsize):
   huffcode= []
   k= 0
   code= 0

   for i in range(len(huffsize)):
      si= huffsize[i]
      for k in range(si):
         huffcode.append((i+1,code))
         code+= 1

      code<<= 1

   return huffcode


def read_dqt(file):
   global q_table

   Lq= read_word(file)
   Lq-= 2
   while Lq>0:
      table= []
      Tq= read_byte(file)
      Pq= Tq >> 4
      Tq&= 0xF
      Lq-= 1

      if Pq==0:
         for i in range(64):
            table.append(read_byte(file))
            Lq-= 1

      else:
         for i in range(64):
            val= read_word(file)
            table.append(val)
            Lq-= 2   

      q_table[Tq]= table


def read_sof(type, file):
   global component
   global XYP

   Lf= read_word(file)
   Lf-= 2
   P= read_byte(file)
   Lf-= 1
   Y= read_word(file)
   Lf-= 2
   X= read_word(file)
   Lf-= 2
   Nf= read_byte(file)
   Lf-= 1

   XYP= X, Y, P
   print XYP

   while Lf>0:
      C= read_byte(file)
      V= read_byte(file)
      Tq= read_byte(file)
      Lf-= 3
      H= V >> 4
      V&= 0xF
      component[C]= {}
      component[C]['H']= H
      component[C]['V']= V
      component[C]['Tq']= Tq


def read_app(type, file):
   Lp= read_word(file)
   Lp-= 2

   if type==0:
      identifier= file.read(5)
      Lp-= 5
      version= file.read(2)
      Lp-= 2
      units= ord(file.read(1))
      Lp-= 1
      Xdensity= ord(file.read(1)) << 8
      Xdensity|= ord(file.read(1))
      Lp-= 2
      Ydensity= ord(file.read(1)) << 8
      Ydensity|= ord(file.read(1))
      Lp-= 2

   file.seek(Lp, 1)


def read_dnl(file):
   global XYP

   Ld= read_word(file)
   Ld-= 2
   NL= read_word(file)
   Ld-= 2

   X, Y, P= XYP

   if Y==0:
      XYP= X, NL, P


def read_sos(file):
   global component
   global num_components
   global dc

   Ls= read_word(file)
   Ls-= 2
   Ns= read_byte(file)
   Ls-= 1

   for i in range(Ns):
      Cs= read_byte(file)
      Ls-= 1
      Ta= read_byte(file)
      Ls-= 1
      Td= Ta >> 4
      Ta&= 0xF
      component[Cs]['Td']= Td
      component[Cs]['Ta']= Ta

   Ss= read_byte(file)
   Ls-= 1
   Se= read_byte(file)
   Ls-= 1
   A= read_byte(file)
   Ls-= 1

   print "Ns:%d Ss:%d Se:%d A:%02X" % (Ns, Ss, Se, A)
   num_components= Ns
   dc= [0 for i in range(num_components+1)]


def calc_add_bits(len, val):
   if (val & (1 << len-1)):
      pass
   else:
      val-= (1 << len) -1

   return val


def bit_read(file):
   global EOI
   global dc
   global inline_dc

   input= file.read(1)
   while input and not EOI:
      if input==chr(0xFF):
         cmd= file.read(1)
         if cmd:
            if cmd==chr(0x00):
               input= chr(0xFF)
            elif cmd==chr(0xD9):
               EOI= True
            elif 0xD0 <= ord(cmd) <= 0xD7 and inline_dc:
               dc= [0 for i in range(num_components+1)]
               input= file.read(1)
	    else:
               input= file.read(1)
               print "CMD: %x" % ord(cmd)

      if not EOI:
         for i in range(7, -1, -1):
            yield (ord(input) >> i) & 0x01

         input= file.read(1)
 
   while True:
      yield []


def get_bits(num, gen):
   out= 0
   for i in range(num):
      out<<= 1
      val= gen.next()
      if val!= []:
         out+= val & 0x01
      else:
         return []

   return out


def print_and_pause(fn):
   def new(*args):
      x= fn(*args)
      print x
      raw_input()
      return x
   return new


#@print_and_pause
def read_data_unit(comp_num):
   global bit_stream
   global component
   global dc

   data= []

   comp= component[comp_num]   
   huff_tbl= huffman_dc_tables[comp['Td']]

   while len(data)< 64:
      key= 0

      for bits in range(1, 17):
         key_len= []
         key<<= 1
         val= get_bits(1, bit_stream)
         if val==[]:
            break
         key|= val
         if huff_tbl.has_key((bits,key)):
            key_len= huff_tbl[(bits,key)]
            break

      huff_tbl= huffman_ac_tables[comp['Ta']]

      if key_len==[]:
         print (bits, key, bin(key)), "key not found"
         break
      elif key_len==0xF0:
         for i in range(16):
            data.append(0)
         continue

      if len(data)!=0:
         if key_len==0x00:
            while len(data)< 64:
               data.append(0)
            break

         for i in range(key_len >> 4):
            if len(data)<64:
               data.append(0)
         key_len&= 0x0F


      if len(data)>=64:
         break

      if key_len!=0:
         val= get_bits(key_len, bit_stream)
         if val==[]:
            break
         num= calc_add_bits(key_len, val)
         
         if len(data)==0 and inline_dc:
            num+= dc[comp_num]
            dc[comp_num]= num

         data.append(num)
      else:
         data.append(0)

   if len(data)!=64:
      print "Wrong size", len(data)

   return data


def restore_dc(data):
   dc_prev= [0 for x in range(len(data[0]))]
   out= []

   for mcu in data:
      for comp_num in range(len(mcu)):
         for du in range(len(mcu[comp_num])):
            if mcu[comp_num][du]:
               mcu[comp_num][du][0]+= dc_prev[comp_num]
               dc_prev[comp_num]= mcu[comp_num][du][0]

      out.append(mcu)

   return out


def read_mcu():
   global component
   global num_components
   global mcus_read

   print "mcu:", mcus_read

   comp_num= mcu= range(num_components)
         
   for i in comp_num:
      comp= component[i+1]
      mcu[i]= []
      for j in range(comp['H']*comp['V']):     
         if not EOI:
            mcu[i].append(read_data_unit(i+1))

#   if 9<=mcus_read<=10:
#      print mcu

   mcus_read+= 1

   return mcu


def dequantify(mcu):
   global component

   out= mcu

   for c in range(len(out)):
      for du in range(len(out[c])):
         for i in range(len(out[c][du])):
            out[c][du][i]*= q_table[component[c+1]['Tq']][i]

   return out


def zagzig(du):
   map= [[ 0,  1,  5,  6, 14, 15, 27, 28],
         [ 2,  4,  7, 13, 16, 26, 29, 42],
         [ 3,  8, 12, 17, 25, 30, 41, 43],
         [ 9, 11, 18, 24, 31, 40, 44, 53],
         [10, 19, 23, 32, 39, 45, 52, 54],
         [20, 22, 33, 38, 46, 51, 55, 60],
         [21, 34, 37, 47, 50, 56, 59, 61],
         [35, 36, 48, 49, 57, 58, 62, 63]]

   for x in range(8):
      for y in range(8):
         if map[x][y]<len(du):
            map[x][y]= du[map[x][y]]
         else:
            map[x][y]= 0

   return map


def for_each_du_in_mcu(mcu, func):
   out= [ [ 0 for du in comp ] for comp in mcu ]

   for comp in range(len(out)):
      for du in range(len(out[comp])):
         out[comp][du]= func(mcu[comp][du])

   return out


def C(x):
   if x==0:
      return 1.0/sqrt(2.0)
   else:
      return 1.0

idct_table= [ [(C(u)*cos(((2.0*x+1.0)*u*pi)/16.0)) for x in range(8)] for u in range(8) ]


def idct(matrix):
   global idct_precision
   out= [ [0 for x in y] for y in matrix]

   for x in range(8):
      for y in range(8):
         sum= 0

         for u in range(idct_precision):
            for v in range(idct_precision):
               sum+= matrix[v][u]*idct_table[u][x]*idct_table[v][y]

         out[y][x]= sum//4

   return out


def expand(mcu, H, V):
   Hout= max(H)
   Vout= max(V)
   out= [ [ [] for x in range(8*Hout) ] for y in range(8*Vout) ]

   for i in range(len(mcu)):
      Hs= Hout//H[i]
      Vs= Vout//V[i]
      Hin= H[i]
      Vin= V[i]
      comp= mcu[i]

      if len(comp)!=(Hin*Vin):
         return []

      for v in range(Vout):
         for h in range(Hout):
            for y in range(8):
               for x in range(8):
                  out[y+v*8][x+h*8].append(comp[(h//Hs)+Hin*(v//Vs)][y//Vs][x//Hs])

   return out


def combine_mcu(mcu):
   global num_components

   H= []
   V= []

   for i in range(num_components):
      H.append(component[i+1]['H'])
      V.append(component[i+1]['V'])

   return expand(mcu, H, V)


def combine_blocks(data):
   global XYP

   X, Y, P= XYP   

   out= [ [ (0, 0, 0) for x in range(X+32) ] for y in range(Y+64) ]
   offsetx= 0
   offsety= 0

   for block in data:
      ybmax= len(block)
      for yb in range(ybmax):
         xbmax= len(block[yb])
         for xb in range(xbmax):
            out[yb+offsety][xb+offsetx]= tuple(block[yb][xb])
      offsetx+= xbmax
      if offsetx>X:
         offsetx= 0
         offsety+= ybmax

   return out


def crop_image(data):
   global XYP
   global Xdensity
   global Ydensity

   X, Y, P= XYP
   return [ [ data[y][x] for x in range(X) ] for y in range(Y) ]


def clip(x):
   if x>255:
      return 255
   elif x<0:
      return 0
   else:
      return x


def YCbCr2RGB(Y, Cb, Cr):
   Cred= 0.299
   Cgreen= 0.587
   Cblue= 0.114

   R= Cr*(2-2*Cred)+Y
   B= Cb*(2-2*Cblue)+Y
   G= (Y-Cblue*B-Cred*R)/Cgreen

   R, G, B= clip(R+128), clip(G+128), clip(B+128)

   return int(R), int(G), int(B)


def YCbCr2Y(Y, Cb, Cr):
   return Y, Y, Y


def for_each_pixel(data, func):
#   out= copy.deepcopy(data)
   out= [ [0 for pixel in range(len(data[0]))] for line in range(len(data))]

   for line in range(len(data)):
      for pixel in range(len(data[0])):
         out[line][pixel]= func(*data[line][pixel])

   return out


def tuplify(data):
   out= []

   for line in data:
      out.append(tuple(line))

   return tuple(out)


def prepare(x, y, z):
   return "#%02x%02x%02x" % (x, y, z)


def display_image(data):
   global XYP
 
   X, Y, P= XYP

   root= Tk()
   im= PhotoImage(width=X, height=Y)

   im.put(data)

   w= Label(root, image=im, bd=0)
   w.pack()

   mainloop()


input_filename= sys.argv[1]
input_file= open(input_filename, "rb")
in_char= input_file.read(1)

while in_char:
   if in_char==chr(0xff):
      in_char= input_file.read(1)
      in_num= ord(in_char)
      if in_num==0xd8:
         print "SOI",
      elif 0xe0<=in_num<=0xef:
         print "APP%x" % (in_num-0xe0),
         read_app(in_num-0xe0, input_file)
      elif 0xd0<=in_num<=0xd7:
         print "RST%x" % (in_num-0xd0),
      elif in_num==0xdb:
         print "DQT",
         read_dqt(input_file)
      elif in_num==0xdc:
         print "DNL",
         read_dnl(input_file)
      elif in_num==0xc4:
         print "DHT",
         read_dht(input_file)
      elif in_num==0xc8:
         print "JPG",
      elif in_num==0xcc:
         print "DAC"
      elif 0xc0<=in_num<=0xcf:
         print "SOF%x" % (in_num-0xc0),
         read_sof(in_num-0xc0, input_file)
      elif in_num==0xda:
         print "SOS",
         read_sos(input_file)
         bit_stream= bit_read(input_file)
         while not EOI:
            data.append(read_mcu())
      elif in_num==0xd9:
         print "EOI",

      print "FF%02X" % in_num

   in_char= input_file.read(1)

input_file.close()

print "AC Huffman tables:", huffman_ac_tables
print "DC Huffman tables:", huffman_dc_tables
print "Quantiztion tables:", q_table
#print "Component table:", component

if not inline_dc:
   print "restore dc"
   data= restore_dc(data)

print "dequantify"
data= [dequantify(mcu) for mcu in data]

print "deserialize"
data= [for_each_du_in_mcu(mcu, zagzig) for mcu in data]

print "inverse discrete cosine transform"
data= [for_each_du_in_mcu(mcu, idct) for mcu in data]

print "combine mcu"
data= [combine_mcu(mcu) for mcu in data]

print "combine blocks"
data= combine_blocks(data)

print "crop image"
data= crop_image(data)

print "color conversion"
data= for_each_pixel(data, YCbCr2RGB)
#data= for_each_pixel(data, YCbCr2Y)

print "prepare"
data= for_each_pixel(data, prepare)

print "tuplify"
data= tuplify(data)

display_image(data)
