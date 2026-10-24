import copy
import unittest
from test_drafts_and_data import blank
from authoring_actions import compile_actions
from authoring_intent import validate_page_intent
from provider_service import ProviderError
from studio_contract import apply_changes

def canvas():
    doc=blank()['definition'];doc['layout']={'layoutDefinitions':{'layout_main':{'type':'absolute','options':{'width':1200,'height':800},'structure':[]}},'tabs':{'items':[{'layoutId':'layout_main','label':'Overview'}]}}
    return doc

class PageCompletionTests(unittest.TestCase):
    def test_page_can_refer_to_a_new_button_created_atomically_in_the_same_batch(self):
        original=canvas();original['layout']['future']={'keep':True};before=copy.deepcopy(original)
        page={'op':'page','layoutId':'layout_main','label':'Overview','purpose':'Investigate','moveItems':False,'width':1200,'height':800,
              'items':[{'id':'nav','kind':'input','x':20,'y':20,'w':200,'h':80}]}
        button={'op':'button','id':'nav','label':'Overview','pageId':'layout_main','targetPageId':'layout_main','targetId':'','x':40,'y':40,'w':200,'h':80}
        for actions in ([page,button],[button,page]):
            result=apply_changes(original,compile_actions(original,actions))
            placed=result['layout']['layoutDefinitions']['layout_main']['structure']
            self.assertEqual(len(placed),1)
            self.assertEqual(placed[0]['position'],{'x':40,'y':40,'w':200,'h':80})
            self.assertEqual(result['inputs']['nav']['eventHandlers'][-1]['options']['tabId'],'layout_main')
            self.assertEqual(result['layout']['future'],{'keep':True})
            self.assertEqual(original,before)
        with self.assertRaisesRegex(ProviderError,'nav'):compile_actions(original,[page])
        invalid=dict(button,targetPageId='missing')
        with self.assertRaises(ProviderError):compile_actions(original,[page,invalid])
        conflict=dict(page,layoutId='other')
        with self.assertRaisesRegex(ProviderError,'consistent placement'):compile_actions(original,[conflict,button])
        self.assertEqual(original,before)
    def test_incomplete_page_count_is_rejected_but_a_clarifying_question_can_leave_canvas_unchanged(self):
        previous=canvas();doc=copy.deepcopy(previous);doc['title']='New goal'
        with self.assertRaisesRegex(ProviderError,'at least 2 pages'):validate_page_intent('Create a board with two pages','Created',doc,previous,{'kind':'dashboard'})
        validate_page_intent('Create a board with two pages','Which units?',previous,previous,{'kind':'dashboard'})
        validate_page_intent('Do not create two pages','Updated',doc,previous,{'kind':'dashboard'})
    def test_explicit_page_purposes_and_named_return_destination_are_checked(self):
        previous=canvas();doc=copy.deepcopy(previous);doc['title']='Goal';doc['layout']['tabs']['items']=[{'label':'Overview','layoutId':'layout_main'},{'label':'Details','layoutId':'details'}];doc['layout']['layoutDefinitions']['details']={'type':'absolute','structure':[]}
        with self.assertRaisesRegex(ProviderError,'purpose'):validate_page_intent('Create with two pages. Page purposes: overview and detail','Created',doc,previous,{'kind':'dashboard'}, {})
        button={'op':'button','id':'nav','label':'Details','pageId':'layout_main','targetPageId':'details','targetId':'','x':20,'y':20,'w':200,'h':80}
        doc=apply_changes(doc,compile_actions(doc,[button]))
        with self.assertRaisesRegex(ProviderError,'targetPageId=layout_main'):validate_page_intent('Add a return-to-Overview button','Added',doc,previous,{'kind':'dashboard'})
    def test_new_button_can_grow_vertical_canvas_without_moving_other_elements(self):
        doc=canvas();doc['layout']['layoutDefinitions']['layout_main']['options']={'width':1200,'height':800}
        button={'op':'button','id':'return','label':'Overview','pageId':'layout_main','targetPageId':'layout_main','targetId':'','x':20,'y':760,'w':200,'h':30}
        result=apply_changes(doc,compile_actions(doc,[button]));page=result['layout']['layoutDefinitions']['layout_main']
        self.assertEqual(page['options']['height'],860)
        self.assertEqual(page['structure'][0]['position'],{'x':20,'y':760,'w':200,'h':80})
        button['x']=1100
        with self.assertRaisesRegex(ProviderError,'width'):compile_actions(doc,[button])
    def test_exact_source_page_and_destination_layout_alias_compiles_correct_row_link(self):
        doc=canvas();doc['visualizations']={'table':{'type':'splunk.table'}}
        doc['layout']['layoutDefinitions']['layout_main']['structure']=[{'item':'table'}]
        doc['layout']['layoutDefinitions']['detail']={'type':'absolute','structure':[]};doc['layout']['tabs']['items'].append({'layoutId':'detail','label':'Details'})
        link={'op':'link','sourceId':'table','pageId':'layout_main','targetId':'detail','field':'entity','token':'selected'}
        result=apply_changes(doc,compile_actions(doc,[link]))
        handlers=result['visualizations']['table']['eventHandlers']
        self.assertEqual(handlers[-1]['options']['tabId'],'detail')
        self.assertEqual(handlers[0]['options']['tokens'][0],{'token':'selected','key':'row.entity.value'})
        # An existing element with that same ID cannot be mistaken for a page.
        doc['visualizations']['detail']={'type':'splunk.markdown'}
        with self.assertRaisesRegex(ProviderError,'ELEMENT'):compile_actions(doc,[link])
