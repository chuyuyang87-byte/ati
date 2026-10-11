import copy
import unittest
import numpy as np
from modules.story_director import validate_storyboard,KEYS
from modules.tts_engine import cue_events,group_words
from modules.animated_renderer import Animator
from modules.story_director import load_profile

class DirectorTests(unittest.TestCase):
 def fixture(self):
  page={'number':7,'text':'Method A 82.88\nMethod B 84.37\nDomain gap in medical image segmentation.'}
  scenes=[]
  for i,module in enumerate(KEYS):
   scenes.append({'id':str(i),'module':module,'title':'为什么会出错','narration':f'换医院后为什么出错？这是第{i}点解释。','visual':'question','labels':['医院A','医院B'],'beats':[{'cue':'换医院','action':'contrast'}],'citations':[{'page':7,'quote':'Domain gap in medical image segmentation.'}]})
  # Only the first is the hook; later scenes develop different ideas.
  for i,s in enumerate(scenes[1:],1):s['narration']=f'第{i}点解释中，换医院意味着图片风格不同。'
  return {'hook':'为什么换医院就失灵','promise':'看懂原因','analogy':'像换城市认路','ending':'要适应新环境','scenes':scenes},[page]
 def test_fabricated_page_rejected(self):
  script,pages=self.fixture();script['scenes'][2]['citations'][0]['page']=8
  with self.assertRaisesRegex(ValueError,'指定原文'):validate_storyboard(script,pages)
 def test_unsupported_metric_rejected(self):
  script,pages=self.fixture();s=script['scenes'][2]
  s.update(visual='comparison',metric_name='DSC',metrics=[{'label':'A','value':82.88},{'label':'B','value':99.99}],citations=[{'page':7,'quote':'Method A 82.88'},{'page':7,'quote':'Method B 84.37'}])
  with self.assertRaisesRegex(ValueError,'99.99'):validate_storyboard(script,pages)
 def test_wrong_narrative_order_rejected(self):
  script,pages=self.fixture();script['scenes'][1],script['scenes'][2]=script['scenes'][2],script['scenes'][1]
  with self.assertRaisesRegex(ValueError,'五模块'):validate_storyboard(script,pages)
 def test_cue_uses_word_time(self):
  words=[{'text':'换','start':.4,'end':.6},{'text':'医院','start':.6,'end':1.0},{'text':'就失灵','start':1.0,'end':1.6}]
  events=cue_events([{'cue':'医院','action':'contrast'}],words)
  self.assertEqual(events[0]['time'],.6)
  with self.assertRaises(ValueError):cue_events([{'cue':'不存在','action':'reveal'}],words)
  captions=group_words(words,4);self.assertEqual(''.join(x['text'] for x in captions),'换医院就失灵')
 def test_graph_moves_inside_scene(self):
  scene={'visual':'graph','title':'相似的放一起','labels':['第一组','第二组','第三组']}
  renderer=Animator(scene,load_profile('science_short'))
  first=np.asarray(renderer.draw(.2,8));last=np.asarray(renderer.draw(6,8))
  # Exclude subtitles and the bottom progress strip; graph nodes themselves move.
  self.assertGreater(np.count_nonzero(first[390:850]!=last[390:850]),5000)
