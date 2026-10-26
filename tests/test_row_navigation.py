"""Synthetic focused tools: native/search guards still run and preserve old work."""
import copy,json,unittest
from agent_service import AgentService
from authoring_actions import compile_actions
from studio_contract import apply_changes
from provider_service import ProviderError
from test_drafts_and_data import blank
from test_reliability_journey import Provider,reply
from test_search_chart_actions import PROFILE
import row_navigation


class Runtime:
    def __init__(self):self.calls=[]
    def environment(self):return {'version':'10.4.4','features':{}}
    def datasets(self):return {'indexes':[{'name':'fixture_index'}]}
    def preview(self,body):
        self.calls.append(body)
        if body.get('fieldDiscovery'):return {'fields':[{'name':'entity'},{'name':'value_ms'}],'results':[{'entity':'PRIVATE_ROW_VALUE','value_ms':0}],'state':'complete'}
        return {'fields':[{'name':'entity'},{'name':'count'}],'results':[{'entity':'PRIVATE_ROW_VALUE','count':2}],'state':'complete'}


class RowNavigationTests(unittest.TestCase):
    def document(self):
        actions=[{'op':'search','id':'events','pipeline':'| stats count BY entity'},
                 {'op':'chart','id':'summary','chartType':'splunk.table','title':'Summary','description':'Observations','sourceId':'events','x':'','y':['entity','count']},
                 {'op':'page','layoutId':'layout_main','label':'Overview','purpose':'Summarize','moveItems':False,'width':1200,'height':800,'items':[{'id':'summary','kind':'block','x':20,'y':20,'w':1160,'h':300}]}]
        return apply_changes(blank()['definition'],compile_actions(blank()['definition'],actions,PROFILE))
    def prompt(self):return 'Make "Summary" open a focused detail page from a table row. Use an actual verified row field for a native token filter, apply that filter to the detail searches, and add return navigation. Keep the current data, time range and standing requirements; preserve the rest of the dashboard.'
    def actions(self):return [
        {'op':'search','id':'detail','pipeline':'| stats count BY entity'},
        {'op':'chart','id':'detail_table','chartType':'splunk.table','title':'Detail','description':'Selected entity','sourceId':'detail','x':'','y':['entity','count']},
        {'op':'page','layoutId':'details','label':'Details','purpose':'Investigate','moveItems':False,'width':1200,'height':800,'items':[{'id':'detail_table','kind':'block','x':20,'y':20,'w':1160,'h':300}]},
        {'op':'token','name':'selected_entity','value':'*'},
        {'op':'filter','sourceId':'detail','field':'entity','token':'selected_entity'},
        {'op':'link','sourceId':'summary','pageId':'details','targetId':'','field':'entity','token':'selected_entity'},
        {'op':'button','id':'back','label':'Back','pageId':'details','targetPageId':'layout_main','targetId':'','x':20,'y':350,'w':160,'h':80}]
    def test_typed_turn_rejects_native_rebinding_then_validates_complete_filtered_navigation(self):
        original=self.document();original['visualizations']['summary']['futureSetting']={'keep':True}
        provider=Provider([reply([{'op':'set','path':'/visualizations/summary/dataSources/primary','value':'events'}]),reply(self.actions())]);runtime=Runtime()
        result=AgentService(provider,runtime).assist({'prompt':self.prompt(),'revision':0,'definition':original,'selected':'summary','dataContext':PROFILE['scope']})
        doc=apply_changes(original,result['changes']);row_navigation.validate_result(doc,original,'summary')
        self.assertEqual(result['recovery']['modelCalls'],2);self.assertEqual(len(doc['layout']['tabs']['items']),2)
        choices=provider.requests[0]['text']['format']['schema']['properties']['changes']['items']['anyOf']
        self.assertTrue(all(set(choice['properties']['op']['enum'])<=row_navigation.OPS for choice in choices))
        self.assertEqual(doc['dataSources']['events'],original['dataSources']['events'])
        self.assertEqual(doc['visualizations']['summary']['futureSetting'],{'keep':True})
        self.assertIn('| search entity=$selected_entity|s$',doc['dataSources']['detail']['options']['query'])
        self.assertNotIn('PRIVATE_ROW_VALUE',json.dumps(provider.requests));self.assertNotIn('details',original['layout']['layoutDefinitions'])
    def test_evidence_and_exact_goal_are_required_and_incomplete_or_unrelated_work_is_rejected(self):
        doc=self.document();profile=dict(PROFILE,fields=[{'name':'entity'}]);receipt={'fields':[{'name':'entity','numeric':False}]}
        self.assertTrue(row_navigation.eligible(self.prompt(),doc,'summary',profile,receipt,[]))
        self.assertFalse(row_navigation.eligible(self.prompt()+' Add a map.',doc,'summary',profile,receipt,[]))
        self.assertFalse(row_navigation.eligible(self.prompt(),doc,'summary',dict(profile,scope={'language':'spl2'}),receipt,[]))
        self.assertFalse(row_navigation.eligible(self.prompt(),doc,'summary',profile,{'fields':[]},[]))
        for action in ({'op':'search','id':'events'},{'op':'chart','id':'summary'},{'op':'page','layoutId':'layout_main'},{'op':'filter','sourceId':'events'}):
            with self.subTest(action=action),self.assertRaises(ProviderError):row_navigation.validate_actions([action],doc,'summary')
        with self.assertRaisesRegex(ProviderError,'button.pageId places Back on the NEW detail page; button.targetPageId'):
            row_navigation.validate_actions([dict(self.actions()[-1],pageId='layout_main')],doc,'summary')
        with self.assertRaises(ProviderError):row_navigation.validate_result(doc,doc,'summary')
        good=apply_changes(doc,compile_actions(doc,self.actions(),profile));good['dataSources']['detail']['options']['query']='search index="fixture_index" | stats count BY entity'
        with self.assertRaises(ProviderError):row_navigation.validate_result(good,doc,'summary')
