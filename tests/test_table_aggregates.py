"""Bounded exact aggregate intent still uses native, search and output validation."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'splunk/constellation/bin'))
from table_aggregates import exact_table_aggregates
from studio_contract import apply_changes
from test_drafts_and_data import blank


class ExactTableAggregateTests(unittest.TestCase):
    def setUp(self):
        self.prompt='For only this selected table, add minimum and maximum duration columns named minimum_duration and maximum_duration alongside its existing summary columns. Keep every original output field and calculation. Preserve all pages, geometry, inputs, tokens, drilldowns, other chart options and unrelated searches.'
        self.profile={'baseQuery':'search index="fixture_index"','scope':{'index':'fixture_index','earliest':'-24h','language':'spl'},'fields':[{'name':'duration','numeric':True}]}
        self.receipt={'status':'complete','table':'table','source':'source','fields':[{'name':'mean_duration'}]}
        self.document=dict(blank()['definition'],visualizations={'table':{'type':'splunk.table','title':'Duration','dataSources':{'primary':'source'},'options':{'table':'> primary | frameBySeriesNames("host", "mean_duration")','future':{'keep':True}},'eventHandlers':[{'future':'keep'}]}},dataSources={'source':{'type':'ds.search','options':{'query':'search index="fixture_index" | stats avg(duration) AS mean_duration BY host','queryParameters':{'earliest':'-24h','latest':'now'}},'future':{'keep':True}}},layout={'type':'grid','structure':[{'item':'table'}]})

    def proposal(self,**kwargs):
        args=dict(prompt=self.prompt,selected='table',document=self.document,profile=self.profile,receipt=self.receipt,attachments=[]);args.update(kwargs)
        return exact_table_aggregates(**args)

    def test_existing_stats_grouping_and_unknown_work_are_preserved(self):
        before=copy.deepcopy(self.document);proposal=self.proposal();self.assertIsNotNone(proposal)
        final=apply_changes(before,proposal['changes'])
        self.assertEqual(final['dataSources']['source']['options']['query'],'search index="fixture_index" | stats avg(duration) AS mean_duration min(duration) AS minimum_duration max(duration) AS maximum_duration BY host')
        expected=copy.deepcopy(before);expected['dataSources']['source']['options']['query']=final['dataSources']['source']['options']['query']
        self.assertEqual(final,expected);self.assertEqual(self.document,before)

    def test_shared_source_is_cloned_for_visualization_input_or_chain_consumers(self):
        for consumer in ('visualization','input','chain'):
            with self.subTest(consumer=consumer):
                doc=copy.deepcopy(self.document)
                if consumer=='visualization':doc['visualizations']['other']={'type':'splunk.bar','dataSources':{'primary':'source'}}
                elif consumer=='input':doc['inputs']={'other':{'type':'input.dropdown','dataSources':{'primary':'source'}}}
                else:doc['dataSources']['child']={'type':'ds.chain','options':{'extend':'source','query':'| head 3'}}
                final=apply_changes(doc,self.proposal(document=doc)['changes']);target=final['visualizations']['table']['dataSources']['primary']
                self.assertNotEqual(target,'source');self.assertEqual(final['dataSources']['source'],doc['dataSources']['source'])
                expected=copy.deepcopy(doc);expected['dataSources'][target]=final['dataSources'][target];expected['visualizations']['table']['dataSources']['primary']=target
                self.assertEqual(final,expected)

    def test_masks_post_calculations_and_literal_projection_are_retained(self):
        from measurement_constraints import mask_command
        self.profile['measurementConstraints']=[{'field':'duration','maximum':150,'unit':'ms'}]
        mask=mask_command(self.profile['measurementConstraints'][0])
        self.document['dataSources']['source']['options']['query']='search index="fixture_index" | '+mask+' | stats avg(duration) AS mean_duration BY host | eval mean_duration=round(mean_duration,2) | sort host | head 10 | table host mean_duration'
        final=apply_changes(self.document,self.proposal()['changes']);query=final['dataSources']['source']['options']['query']
        self.assertIn('| '+mask+' | stats',query);self.assertIn('BY host | eval mean_duration=round(mean_duration,2) | sort host | head 10 | table host mean_duration minimum_duration maximum_duration',query)

    def test_ambiguous_unverified_mixed_or_complex_requests_fall_back(self):
        for prompt in [self.prompt+' Add another chart.',self.prompt.replace('Keep every original output field and calculation.','Also filter hosts.'),self.prompt.replace('minimum_duration and maximum_duration','minimum_duration'),self.prompt.replace('duration columns','unknown columns'),'Sort this table and '+self.prompt,self.prompt.replace('For only this selected table, ','')]:
            with self.subTest(prompt=prompt):self.assertIsNone(self.proposal(prompt=prompt))
        for change in ('attachment','receipt','language','numeric','complex','report','alias','scope'):
            doc=copy.deepcopy(self.document);profile=copy.deepcopy(self.profile);receipt=copy.deepcopy(self.receipt);attachments=[]
            if change=='attachment':attachments=[{'name':'fixture.pdf'}]
            elif change=='receipt':receipt['source']='other'
            elif change=='language':profile['scope']['language']='spl2'
            elif change=='numeric':profile['fields'][0]['numeric']=False
            elif change=='complex':doc['dataSources']['source']['options']['query']+=' | where mean_duration>0'
            elif change=='report':doc['dataSources']['source']['type']='ds.savedSearch'
            elif change=='alias':doc['dataSources']['source']['options']['query']+=' | eval minimum_duration=1'
            else:profile['baseQuery']='search index="different"';profile['scope']['index']='different'
            with self.subTest(change=change):self.assertIsNone(self.proposal(document=doc,profile=profile,receipt=receipt,attachments=attachments))
        doc=copy.deepcopy(self.document);doc['dataSources']['source']['options']['query']='search index="fixture_index" | stats avg(duration_ms) AS ms avg(duration_seconds) AS seconds'
        profile=dict(self.profile,fields=[{'name':n,'numeric':True}for n in ('duration_ms','duration_seconds')])
        self.assertIsNone(self.proposal(document=doc,profile=profile))

    def test_agent_uses_zero_model_calls_but_verifies_and_displays_outputs(self):
        from test_reliability_journey import Provider,Runtime
        from agent_service import AgentService
        class Outputs(Runtime):
            def preview(self,body):
                if body.get('fieldDiscovery'):return super().preview(body)
                self.calls.append(body);names=['host','mean_duration']
                if 'min(duration)'in body['query']:names+=['minimum_duration','maximum_duration']
                return {'state':'complete','fields':[{'name':n}for n in names],'results':[dict(zip(names,['fixture-host','20','10','30']))]}
        for provider_name in ('openai','ollama','aitk'):
            with self.subTest(provider=provider_name):
                provider=Provider([]);provider.configured=lambda:{'provider':provider_name,'model':'synthetic-model'};runtime=Outputs()
                result=AgentService(provider,runtime).assist({'prompt':self.prompt,'definition':self.document,'revision':0,'selected':'table','dataContext':self.profile['scope']})
                final=apply_changes(self.document,result['changes'])
                self.assertEqual(result['recovery']['modelCalls'],0);self.assertFalse(provider.requests)
                self.assertEqual(result['recovery']['queryChecks'],2)
                self.assertIn('"minimum_duration", "maximum_duration"',final['visualizations']['table']['options']['table'])
                self.assertEqual(final['visualizations']['table']['eventHandlers'],self.document['visualizations']['table']['eventHandlers'])
