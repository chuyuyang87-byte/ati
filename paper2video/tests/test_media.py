import tempfile
import unittest
from pathlib import Path
from modules.tts_engine import sentences, timestamp,write_srt
from modules.video_maker import render_scene_card

class MediaTests(unittest.TestCase):
 def test_caption_preserves_text(self):
  text='长句没有标点也不能丢字'*12+'。第二句！'
  self.assertEqual(''.join(sentences(text)),text)
 def test_srt_millisecond_carry(self):
  self.assertEqual(timestamp(59.9999),'00:01:00,000')
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'captions.srt'
   write_srt([dict(start=0,end=1.5,text='你好')],p)
   self.assertIn('00:00:00,000 --> 00:00:01,500',p.read_text())
 def test_overflow_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):
    render_scene_card(dict(title='标题',bullets=['超长文本'*300]),Path(d)/'card.png')
