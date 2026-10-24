"""Synthetic independent-population requirements and bounded model recovery."""
import copy
import unittest
from agent_service import AgentService
from population_guard import independent_measurements, validate_populations
from provider_service import ProviderError
from studio_contract import apply_changes
from test_drafts_and_data import blank
from test_reliability_journey import Provider, Runtime, reply
from test_search_chart_actions import chart, page, PROFILE

PROFILE_WITH_FIELDS=dict(PROFILE,fields=[{'name':'metric_a','numeric':True},{'name':'metric_b','numeric':True},{'name':'entity','numeric':False}])


class PopulationGuardTests(unittest.TestCase):
    def test_explicit_independence_survives_focused_edits_and_allows_a_current_revision(self):
        brief={'purpose':'Exclude high A, but retain B measurements independently.','requirements':''}
        self.assertTrue(independent_measurements('Round the selected table',brief))
        self.assertFalse(independent_measurements('Use the same population for both measurements now.',brief))
        self.assertFalse(independent_measurements('Show counts by entity',{}))

    def test_shared_numeric_filter_is_rejected_but_conditional_aggregates_and_scopes_are_retained(self):
        query='search index="fixture_index" | where metric_a<=150 | stats avg(metric_a) AS average_a latest(metric_b) AS latest_b BY entity'
        with self.assertRaisesRegex(ProviderError,'discards events') as error:validate_populations(query,PROFILE_WITH_FIELDS)
        self.assertEqual(error.exception.code,'population_coupling')
        for suffix in ('| stats avg(eval(if(metric_a<=150,metric_a,null()))) AS average_a latest(metric_b) AS latest_b BY entity',
                       '| search entity="fixture_A" | where metric_a<=150 | stats avg(metric_a) AS average_a',
                       '| eval note="| where metric_a<=150" | stats avg(metric_a) AS average_a latest(metric_b) AS latest_b'):
            validate_populations(PROFILE['baseQuery']+' '+suffix,PROFILE_WITH_FIELDS)
        # An explicit existing-search scope is preserved, not silently widened.
        base='search index="fixture_index" | where metric_a<=150'
        validate_populations(base+' | stats avg(metric_a) latest(metric_b)',dict(PROFILE_WITH_FIELDS,baseQuery=base))
        validate_populations(query,dict(PROFILE_WITH_FIELDS,scope={'language':'spl2'}))

    def test_population_failure_recovers_before_execution_without_changing_the_request(self):
        class NumericRuntime(Runtime):
            def execute(self,query,earliest):
                return {'results':[{'field':item['name'],'count':'20','numeric_count':'20' if item['numeric'] else '0'} for item in PROFILE_WITH_FIELDS['fields']], 'state':'complete'}
            def preview(self,body):
                self.calls.append(copy.deepcopy(body))
                return {'fields':[{'name':'average_a'},{'name':'latest_b'}],'results':[{'average_a':'20','latest_b':'30'}],'state':'complete'}
        original=blank()['definition'];before=copy.deepcopy(original);runtime=NumericRuntime()
        bad=[{'op':'search','id':'events','pipeline':'| where metric_a<=150 | stats avg(metric_a) AS average_a latest(metric_b) AS latest_b'},chart('splunk.table','',['average_a','latest_b']),page()]
        fixed=[{'op':'search','id':'events','pipeline':'| stats avg(eval(if(metric_a<=150,metric_a,null()))) AS average_a latest(metric_b) AS latest_b'}]
        provider=Provider([reply(bad),reply(fixed)])
        result=AgentService(provider,runtime).assist({'prompt':'Exclude A over 150 but retain B measurements independently.','revision':0,'definition':original,'dataContext':blank()['dataContext']})
        self.assertEqual(result['recovery']['modelCalls'],2);self.assertEqual(len(runtime.calls),1)
        self.assertIn('independent measurements',result['validationNotes'][0])
        self.assertIn('metric_b',result['validationNotes'][0])
        self.assertEqual(original,before)
        doc=apply_changes(original,result['changes'])
        self.assertIn('avg(eval(if(',doc['dataSources']['events']['options']['query'])
