import copy
import tempfile
import unittest
from pathlib import Path
from modules.research_contract import validate_research,audit_research
from modules.story_director import load_profile,_prepare
from modules.source_assets import extract_pages,bind_assets
from modules.animated_renderer import Animator

class ResearchTests(unittest.TestCase):
 def fixture(self):
  scenes=[]
  for i,role in enumerate(['term','term','mechanism','evidence','limitation','reproduction']):
   s={'teaching_role':role,'learning_goal':'知道这一环节如何工作','visual_steps':['明确输入','解释输出'],'visual':'source_page' if role in ['mechanism','evidence'] else 'graph','module':'result' if role=='evidence' else 'method','source_page':1,'title':'研究方法','labels':['输入','输出'],'narration':'解释TTA与DSC'}
   if role=='term':s['term_card']={'name':['TTA','DSC'][i],'full_name':'Formal name','definition':'含义','paper_role':'作用','analogy_limit':'不代表实际过程'}
   scenes.append(s)
  return {'scenes':scenes}
 def test_partial_cue_uses_literal_anchor(self):
  s={'narration':'SAR甚至低于无适应基线。','beats':[{'cue':'SAR低于无适应基线','action':'contrast'}],'evidence_ids':['p1l0']}
  prepared=_prepare([s],{'p1l0':{'page':1,'quote':'Original supporting evidence.'}})
  self.assertEqual(prepared[0]['beats'][0]['cue'],'低于无适应基线')
 def test_research_rejects_unexplained_terms(self):
  s=self.fixture();del s['scenes'][0]['term_card']
  with self.assertRaisesRegex(ValueError,'术语卡'):validate_research(s)
 def test_research_requires_original_results(self):
  s=self.fixture();s['scenes'][3]['visual']='graph'
  with self.assertRaisesRegex(ValueError,'原文素材'):validate_research(s)
 def test_teaching_rejection_is_blocking(self):
  class Reviewer:
   def ask_json(self,*args):return {'approved':False,'issues':['没有解释指标']}
  with self.assertRaisesRegex(ValueError,'没有解释指标'):audit_research(self.fixture(),[],Reviewer())
 def test_real_pdf_source_and_integrity(self):
  import pypdfium2 as pdfium
  with tempfile.TemporaryDirectory() as folder:
   doc=pdfium.PdfDocument.new();doc.new_page(300,300);pdf=Path(folder)/'source.pdf';doc.save(pdf);doc.close()
   assets=extract_pages(pdf,Path(folder)/'assets');s=self.fixture();bind_assets(s,assets)
   scene=s['scenes'][2];renderer=Animator(scene,load_profile('research_bridge'))
   self.assertEqual(renderer.draw(1,10).size,(1280,720))
   Path(scene['source_asset']).write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'校验失败'):Animator(scene,load_profile('research_bridge'))
