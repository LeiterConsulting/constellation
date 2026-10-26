import copy
import json
import unittest
from test_reliability_journey import Provider, Runtime, reply
from test_drafts_and_data import blank
from agent_service import AgentService
from studio_contract import apply_changes
from time_axis import verified_time_axes

DOC = {'visualizations': {'trend': {'type': 'splunk.line', 'dataSources': {'primary': 'events'}, 'options': {'x': '> primary | seriesByName("time")', 'y': '> primary | frameBySeriesNames("reading")'}}},
       'dataSources': {'events': {'type': 'ds.search', 'options': {'query': 'search index="fixture_index" | timechart bins=100 avg(value) AS reading'}}}}
RECEIPT = [{'source': 'events', 'status': 'results', 'fields': ['_time', 'reading']}]

class TimeAxisTests(unittest.TestCase):
    def test_only_exact_changed_invalid_axis_is_repaired_from_actual_output(self):
        before = copy.deepcopy(DOC)
        operations = verified_time_axes(DOC, {}, RECEIPT)
        self.assertEqual(len(operations), 1)
        self.assertEqual(json.loads(operations[0]['value']), '> primary | seriesByName("_time")')
        self.assertEqual(DOC, before)
        self.assertEqual(verified_time_axes(DOC, DOC, RECEIPT), [])

    def test_valid_alias_unknown_empty_partial_and_untouched_imports_are_preserved(self):
        for receipt in ([], [{'source':'events','status':'empty','fields':['_time']}], [{'source':'events','status':'partial','fields':['_time']}], [{'source':'events','status':'results','fields':['_time','time','reading']}], [{'source':'events','status':'results','fields':['time','reading']}]):
            self.assertEqual(verified_time_axes(DOC, {}, receipt), [])
        for query in ('search index="fixture_index" | stats count AS reading', 'search index="fixture_index" | eval note="| timechart"'):
            doc=copy.deepcopy(DOC); doc['dataSources']['events']['options']['query']=query
            self.assertEqual(verified_time_axes(doc, {}, RECEIPT), [])
        for binding in ('> primary | seriesByName("Time")', '> primary | seriesByName("time") | lastPoint()', '> other | seriesByName("time")'):
            doc=copy.deepcopy(DOC);doc['visualizations']['trend']['options']['x']=binding
            self.assertEqual(verified_time_axes(doc, {}, RECEIPT), [])

    def test_agent_repairs_axis_without_another_model_call_and_revalidates_search(self):
        class TimeRuntime(Runtime):
            def preview(self, body):
                if body.get('fieldDiscovery'): return super().preview(body)
                if 'timechart' not in body['query']: return super().preview(body)
                return {'state':'complete','fields':[{'name':'_time'},{'name':'reading'}], 'results':[{'_time':'fixture-time','reading':'3'}]}
        changes=[{'op':'search','id':'events','pipeline':'| timechart bins=100 avg(value) AS reading'},
                 {'op':'chart','id':'trend','chartType':'splunk.line','title':'Readings','description':'Fixture','sourceId':'events','x':'time','y':['reading']},
                 {'op':'layout','layoutId':'overview','label':'Overview','width':1200,'height':600,'items':[{'id':'trend','kind':'block','x':20,'y':20,'w':800,'h':300}]}]
        provider=Provider([reply(changes)]);state=blank()
        result=AgentService(provider,TimeRuntime()).assist({'prompt':'Show a reading trend','revision':0,'definition':state['definition'],'dataContext':state['dataContext']})
        final=apply_changes(state['definition'],result['changes'])
        self.assertEqual(final['visualizations']['trend']['options']['x'], '> primary | seriesByName("_time")')
        self.assertEqual(result['recovery']['modelCalls'],1)
        self.assertEqual(result['recovery']['queryChecks'],1)
