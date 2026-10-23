import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from authoring_actions import compile_actions, validate_chart_placement
from studio_contract import apply_changes
from provider_service import ProviderError


class TypedLayoutTests(unittest.TestCase):
    def test_literal_root_text_is_encoded_without_loosening_native_object_validation(self):
        original=self.document()
        actions=[{'op':'set','path':'/title','value':'Freezer monitoring'},
                 {'op':'set','path':'/description','value':'Readings above 150°F are excluded.'}]
        result=apply_changes(original,compile_actions(original,actions))
        self.assertEqual(result['title'],'Freezer monitoring')
        self.assertEqual(result['description'],'Readings above 150°F are excluded.')
        self.assertEqual(actions[0]['value'],'Freezer monitoring')
        for path,value in [('/layout','broken object'),('/description','"unfinished text'),('/title','{"unfinished":')]:
            with self.subTest(path=path,value=value),self.assertRaises(ProviderError):
                apply_changes(original,compile_actions(original,[{'op':'set','path':path,'value':value}]))
    def document(self):
        return {'title':'New dashboard','visualizations':{'metric':{'type':'splunk.markdown','options':{'markdown':'Note'}}},
                'layout':{'future':{'keep':True},'globalInputs':[],'tabs':{'items':[{'layoutId':'layout_main','label':'Overview','future':'keep'}]},
                          'layoutDefinitions':{'layout_main':{'type':'absolute','options':{'width':1200,'height':800,'future':'keep'},
                            'structure':[{'item':'metric','type':'block','position':{'x':20,'y':20,'w':300,'h':200},'future':'keep'}]}}}}
    def action(self,**changes):
        return dict({'op':'layout','layoutId':'layout_main','label':'Overview','width':1200,'height':800,
                     'items':[{'id':'metric','kind':'block','x':20,'y':40,'w':1160,'h':300}]},**changes)
    def test_typed_geometry_compiles_to_valid_native_json_and_preserves_unknown_configuration(self):
        original=self.document(); before=copy.deepcopy(original)
        changes=compile_actions(original,[self.action()]); result=apply_changes(original,changes)
        self.assertEqual(original,before)
        page=result['layout']['layoutDefinitions']['layout_main']
        self.assertEqual(page['structure'][0]['position'],{'x':20,'y':40,'w':1160,'h':300})
        self.assertEqual(page['structure'][0]['future'],'keep');self.assertEqual(page['options']['future'],'keep')
        self.assertEqual(result['layout']['future'],{'keep':True});self.assertEqual(result['layout']['tabs']['items'][0]['future'],'keep')
    def test_new_page_keeps_existing_pages_but_replaces_only_an_empty_startup_scaffold(self):
        document=self.document(); result=apply_changes(document,compile_actions(document,[self.action(layoutId='details',label='Details')]))
        self.assertEqual(len(result['layout']['tabs']['items']),2)
        document['visualizations']={};document['layout']['layoutDefinitions']['layout_main']['structure']=[]
        changes=compile_actions(document,[self.action(layoutId='new_page',items=[])])
        result=apply_changes(document,changes)
        self.assertEqual(list(result['layout']['layoutDefinitions']),['new_page'])
        self.assertEqual(result['layout']['tabs']['items'],[{'layoutId':'new_page','label':'Overview'}])
    def test_invalid_geometry_and_mixed_layout_protocols_are_rejected(self):
        for action in (self.action(width=0), self.action(height=True), self.action(width=100), self.action(items=[{'id':'metric','kind':'block','x':-1,'y':0,'w':100,'h':100}])):
            with self.subTest(action=action), self.assertRaises(ProviderError): compile_actions(self.document(),[action])
        with self.assertRaises(ProviderError): compile_actions(self.document(),[self.action(),{'op':'set','path':'/layout/options','value':'{}'}])

    def test_new_chart_collisions_fail_but_existing_and_conditional_overlays_survive(self):
        document = {'visualizations': {'one': {'type': 'splunk.line'}, 'two': {'type': 'splunk.bar'}},
                    'layout': {'type': 'absolute', 'structure': [
                        {'item': 'one', 'position': {'x': 0, 'y': 0, 'w': 600, 'h': 300}},
                        {'item': 'two', 'position': {'x': 0, 'y': 200, 'w': 600, 'h': 300}}]}}
        with self.assertRaisesRegex(ProviderError, 'separate rectangles'): validate_chart_placement(document, {})
        validate_chart_placement(document, copy.deepcopy(document))
        document['visualizations']['two']['containerOptions'] = {'visibility': {'showConditions': ['toggle']}}
        validate_chart_placement(document, {})
        del document['visualizations']['two']['containerOptions']
        document['layout']['structure'][1]['position']['y'] = 300
        validate_chart_placement(document, {})


if __name__=='__main__':unittest.main()

class InputPlacementTests(unittest.TestCase):
    def test_native_button_height_is_checked_for_new_or_repositioned_inputs(self):
        document={'inputs':{'back':{'type':'input.button'}},'layout':{'type':'absolute','structure':[{'item':'back','position':{'x':0,'y':0,'w':200,'h':40}}]}}
        with self.assertRaisesRegex(ProviderError,'labels are visible'):validate_chart_placement(document,{})
        validate_chart_placement(document,copy.deepcopy(document))
        document['layout']['structure'][0]['position']['h']=80
        validate_chart_placement(document,{})

    def test_new_layout_changes_cannot_cover_navigation_with_a_chart(self):
        document={'visualizations':{'chart':{'type':'splunk.line'}},'inputs':{'back':{'type':'input.button'}},
                  'layout':{'type':'absolute','structure':[{'item':'chart','position':{'x':0,'y':0,'w':500,'h':300}},{'item':'back','position':{'x':0,'y':320,'w':200,'h':40}}]}}
        original=copy.deepcopy(document)
        document['layout']['structure'][0]['position']['h']=400
        with self.assertRaisesRegex(ProviderError,'chart, back'):validate_chart_placement(document,original)
        validate_chart_placement(document,copy.deepcopy(document))
        document['inputs']['back']['containerOptions']={'visibility':{'showConditions':['details']}}
        validate_chart_placement(document,original)
