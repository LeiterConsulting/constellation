"""Synthetic first-map plans preserve assets and pass normal compilation."""
import copy
import unittest
from svg_creation import eligible,expand
from authoring_actions import compile_actions,validate_chart_placement
from studio_contract import apply_changes
from provider_service import ProviderError
from test_drafts_and_data import blank
from test_search_chart_actions import PROFILE
PROFILE=dict(PROFILE,fields=[{'name':'measurement','numeric':True}])

class SvgCreationTests(unittest.TestCase):
    def seed(self):
        doc=blank()['definition'];doc['inputs']={};doc['visualizations']={'map':{'type':'splunk.choropleth.svg','future':{'keep':True},'options':{'svg':'splunk-enterprise-kvstore://fixture'}}};doc['layout']={'globalInputs':[],'tabs':{'items':[{'label':'Overview','layoutId':'main'}]},'layoutDefinitions':{'main':{'type':'absolute','options':{'width':1200,'height':800},'structure':[{'type':'block','item':'map','position':{'x':20,'y':20,'w':500,'h':400}}]}}};return doc
    def test_compilation_preserves_map_and_builds_independent_selection_and_clear(self):
        doc=self.seed();before=copy.deepcopy(doc);field=PROFILE['fields'][0]['name'];plan=dict(op='svgCompose',pageLabel='Ranges',purpose='Synthetic categories',mapTitle='Areas',tableTitle='Summary',pipeline='| eval area="a"',measurementField=field,areaField='area',valueField='readings',selectionToken='selected_area',clearLabel='Clear selection')
        result=apply_changes(doc,compile_actions(doc,expand([plan],doc,PROFILE),PROFILE));self.assertEqual(doc,before);self.assertEqual(result['visualizations']['map']['options']['svg'],before['visualizations']['map']['options']['svg']);self.assertEqual(result['visualizations']['map']['future'],{'keep':True});self.assertEqual(len(result['layout']['tabs']['items']),1);self.assertEqual(result['layout']['tabs']['items'][0]['layoutId'],'main');self.assertEqual(result['defaults']['tokens']['default']['selected_area']['value'],'*');self.assertEqual(len(result['inputs']),1)
        sources=result['dataSources'];self.assertNotIn('$selected_area',sources['constellation_map']['options']['query']);self.assertIn('$selected_area|s$',sources['constellation_detail']['options']['query']);self.assertIn('isnotnull('+field+')',sources['constellation_map']['options']['query']);self.assertIn('stats count AS readings BY area',sources['constellation_map']['options']['query']);validate_chart_placement(result,doc)
        plan['pipeline']='| stats count AS readings BY area'
        with self.assertRaisesRegex(ProviderError,'row-level'):expand([plan],doc,PROFILE)
        plan['pipeline']='| eval area="a"';plan['measurementField']='invented'
        with self.assertRaisesRegex(ProviderError,'inspected source measurement'):expand([plan],doc,PROFILE)
        plan['measurementField']=field;plan['pipeline']='| eval '+field+'=0, area="a"'
        with self.assertRaisesRegex(ProviderError,'without overwriting'):expand([plan],doc,PROFILE)
    def test_only_exact_small_unbound_boards_are_eligible(self):
        doc=self.seed();context={'request':'Build exactly one page with exactly two visualizations: an SVG map and summary table. Count readings. Add Clear selection button.','dataProfile':PROFILE,'svgAssets':[{'areaIds':['a']}]};self.assertTrue(eligible(context,doc))
        for extra in (' Add a dropdown.',' Use custom layout.'):
            self.assertFalse(eligible(dict(context,request=context['request']+extra),doc))
        doc['dataSources']={'existing':{'type':'ds.search'}};self.assertFalse(eligible(context,doc))
        with self.assertRaises(ProviderError):expand([{'op':'set'}],self.seed(),PROFILE)
