import struct,unittest
from mintxp.pe_icons import bitmap_rgba
class BitmapAlpha(unittest.TestCase):
 def bmp(self,pixels,h=1):
  return b'BM'+struct.pack('<IHHI',54+len(pixels),0,0,54)+struct.pack('<IiiHHIIiiII',40,2,h,1,32,0,len(pixels),0,0,0,0)+pixels
 def test_preserves_partial_alpha_and_rgb_without_black_colorkey(self):
  self.assertEqual(bitmap_rgba(self.bmp(bytes([10,20,30,64,0,0,0,255]))),(2,1,bytes([30,20,10,64,0,0,0,255])))
 def test_bottom_up_and_top_down_rows(self):
  a=bytes([1,2,3,255])*2;b=bytes([4,5,6,127])*2
  self.assertEqual(bitmap_rgba(self.bmp(a+b,2)),bitmap_rgba(self.bmp(b+a,-2)))
 def test_legacy_reserved_alpha_falls_back(self):self.assertIsNone(bitmap_rgba(self.bmp(bytes([10,20,30,0])*2)))
 def test_truncated_pixels_rejected(self):
  with self.assertRaises(ValueError):bitmap_rgba(self.bmp(bytes([10,20,30,255])*2)[:-1])
