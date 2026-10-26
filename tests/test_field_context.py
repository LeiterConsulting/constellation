"""Authored field evidence; no lab data, provider calls or credentials."""
import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'splunk/constellation/bin'))
from field_context import enrich_profile,sample_fields,validate_missing_measurements,recorded_unit_intent,recorded_unit_question,unit_confirmation
from provider_service import ProviderError
from data_service import DataService
from dashboard_brief import authoring_brief

class FieldContextTests(unittest.TestCase):
    def profile(self,fields):
        return {'scope':{'index':'fixture','earliest':'-24h'},'fields':fields,'sampledRows':4}
    def test_exact_sample_presence_numeric_zero_invalid_and_multivalue_are_distinct(self):
        result={'fields':[{'name':x}for x in ('temperature_f','signal','ids','_raw')], 'results':[
            {'temperature_f':0,'signal':'-60','ids':['one','two'],'_raw':'PRIVATE FIXTURE'},
            {'temperature_f':'unknown','signal':None,'ids':[]},
            {'temperature_f':float('nan'),'signal':'','ids':'single'},
            {'signal':0}]}
        before=copy.deepcopy(result);fields,rows=sample_fields(result)
        self.assertEqual(rows,4);self.assertEqual({x['name']for x in fields},{'temperature_f','signal','ids'})
        fields=sorted(fields,key=lambda f: {'temperature_f':0,'signal':1,'ids':2}[f['name']])
        self.assertEqual(fields[0]['coverage'],{'missing':1,'numeric':1,'multivalue':0,'basis':'sample_rows'})
        self.assertEqual(fields[1]['coverage']['missing'],2);self.assertEqual(fields[1]['coverage']['numeric'],2)
        self.assertFalse(fields[0]['numeric']);self.assertEqual(fields[2]['coverage']['multivalue'],1)
        self.assertNotIn('PRIVATE',json.dumps(fields));self.assertEqual(result['results'][0],before['results'][0])
    def test_names_supply_hints_and_do_not_establish_status_values_or_units_for_rssi(self):
        p=enrich_profile(self.profile([{'name':n}for n in ('temperature_f','temperature','response_time_ms','wifi_rssi','device_id','pid','status','event_count')]))
        contexts={x['name']:x['context']for x in p['fields']}
        self.assertEqual(contexts['temperature_f']['unit'],'°F');self.assertEqual(contexts['temperature_f']['basis'],'field_name')
        self.assertNotIn('unit',contexts['temperature']);self.assertNotIn('unit',contexts['wifi_rssi'])
        self.assertEqual(contexts['response_time_ms']['unit'],'ms')
        for n in ('pid','device_id'):self.assertEqual(contexts[n]['role'],'identifier')
        self.assertEqual(contexts['status']['role'],'category');self.assertNotIn('meaning',contexts['status'])
        self.assertEqual(contexts['event_count']['role'],'counter')
    def test_only_explicit_exact_field_declarations_are_user_context_and_conflicts_remain_visible(self):
        base=self.profile([{'name':'temperature_f'},{'name':'latency'},{'name':'pid'}]);old=copy.deepcopy(base)
        p=enrich_profile(base,'temperature_f is measured in Celsius. latency is recorded in milliseconds. latency represents elapsed response time. pid is recorded in seconds.')
        a,b,c=[x['context']for x in p['fields']]
        self.assertEqual(a['basis'],'user');self.assertEqual(a['nameUnitConflict'],'°F');self.assertEqual(a['unit'],'°C')
        self.assertEqual(b['meaning'],'elapsed response time');self.assertEqual(b['unit'],'ms');self.assertEqual(c['role'],'identifier')
        self.assertEqual(base,old)
        for intent in ('Convert latency to seconds.','not_latency is measured in seconds.','Our process usually responds in seconds.'):
            with self.subTest(intent=intent):self.assertNotIn('unit',enrich_profile(base,intent)['fields'][1]['context'])
    def test_existing_search_keeps_output_grain_and_does_not_invent_time(self):
        p=self.profile([{'name':'mean_ms','numeric':True,'present':4}]);p['scope']={'query':'search index=fixture | stats avg(value) AS mean_ms','earliest':'-24h'}
        e=enrich_profile(p);self.assertEqual(e['grain'],'existing_search_output');self.assertNotIn('_time',json.dumps(e['fields']))
    def test_user_definitions_and_missing_data_intent_survive_the_rolling_chat(self):
        b=authoring_brief({'brief':{'purpose':'Operational readings','requirements':''},'prompt':'latency is recorded in milliseconds. Each row represents one observation. Missing readings are unknown, never zero.'})
        for text in ('latency is recorded','Each row represents','Missing readings'):self.assertIn(text,b['requirements'])
    def test_index_inspection_uses_current_user_bounded_verbose_preview_and_no_raw_values_escape(self):
        class Runtime:
            calls=[]
            def datasets(self):return {'indexes':[{'name':'fixture'}]}
            def preview(self,body):
                self.calls.append(body)
                return {'fields':[{'name':'_time'},{'name':'temperature_f'},{'name':'_raw'}], 'results':[{'_time':'1000','temperature_f':0,'_raw':'PRIVATE'}], 'state':'partial'}
        r=Runtime();p=DataService(r).profile({'index':'fixture','earliest':'-1h'})
        self.assertEqual(r.calls,[{'query':'search index="fixture" | head 201','language':'spl','earliest':'-1h','fieldDiscovery':True}])
        self.assertEqual(p['sampledRows'],1);self.assertEqual(p['completion']['state'],'partial');self.assertNotIn('PRIVATE',json.dumps(p))

    def test_sparse_measurement_zero_imputation_rejects_without_changing_query_or_count_fields(self):
        profile=enrich_profile(self.profile([{'name':'temperature_f','numeric':True,'present':2,'coverage':{'missing':2}}]))
        for q in ('| fillnull value=0', '| fillnull value=0 temperature_f', '| eval temperature_f=coalesce(temperature_f,0)', '| stats avg(temperature_f) AS mean_f | fillnull value=0 mean_f'):
            with self.subTest(q=q),self.assertRaises(ProviderError):validate_missing_measurements(q,profile)
        for q in ('| stats count AS readings | fillnull value=0 readings', '| eval note="| fillnull value=0"', '| fillnull value="unknown" temperature_f', '| eval note="temperature_f=coalesce(temperature_f,0)"'):
            validate_missing_measurements(q,profile)
        validate_missing_measurements('| fillnull value=0',profile,'spl2')

    def test_definitions_are_scoped_and_roundtrip_separately_from_unconfirmed_brief_words(self):
        p=enrich_profile(self.profile([{'name':'latency'}]),'latency is recorded in ms. latency means time for one observation.')
        self.assertEqual(p['scope']['fieldDefinitions']['latency']['unit'],'ms')
        restored=enrich_profile(p)
        self.assertEqual(restored['fields'][0]['context']['basis'],'user')
        self.assertEqual(restored['fields'][0]['context']['meaning'],'time for one observation')
        other=self.profile([{'name':'latency'}]);other['scope']['index']='other_fixture'
        self.assertNotIn('unit',enrich_profile(other)['fields'][0]['context'])
        from field_context import validate_definitions
        for defs in ({'latency':{'unit':[]}}, {'latency':{'unit':'fortnights'}},{'latency':{'meaning':'x'*241}},{'latency':{'key':'hidden'}}):
            with self.subTest(defs=defs),self.assertRaises(ProviderError):validate_definitions(defs)

    def test_wide_schema_keeps_measurements_over_alphabetically_early_technical_fields(self):
        names=['_technical_'+str(i)for i in range(90)]+['device_name','response_time_ms','status','_raw']
        result={'fields':[{'name':name}for name in names],'results':[{name:'7'for name in names}]}
        fields,rows=sample_fields(result)
        self.assertEqual(rows,1);self.assertEqual(len(fields),60)
        self.assertIn('response_time_ms',[field['name']for field in fields]);self.assertIn('device_name',[field['name']for field in fields])
        self.assertNotIn('_raw',[field['name']for field in fields])

    def test_existing_spl_inspection_is_bounded_without_changing_selected_search_or_grain(self):
        class Runtime:
            calls=[]
            def preview(self,body):
                self.calls.append(body);return {'fields':[{'name':'mean'}],'results':[{'mean':3}],'state':'complete'}
        runtime=Runtime();query='search index=fixture | stats avg(value) AS mean'
        result=DataService(runtime).profile({'query':query,'language':'spl','earliest':'-1h'})
        self.assertEqual(runtime.calls[0]['query'],query+' | head 201')
        self.assertEqual(result['baseQuery'],query);self.assertEqual(result['scope']['query'],query)
        self.assertEqual(result['grain'],'existing_search_output');self.assertNotIn('_time',[f['name']for f in result['fields']])
        DataService(runtime).profile({'query':query,'language':'spl2','earliest':'-1h'})
        self.assertEqual(runtime.calls[-1]['query'],query)

    def test_short_unit_answers_bind_only_after_a_single_recorded_unit_question(self):
        profile=enrich_profile(self.profile([{'name':'temperature','numeric':True,'present':4}]))
        history=[{'role':'assistant','text':'Is temperature recorded in Fahrenheit or Celsius? I will keep the dashboard unchanged until you confirm.'}]
        intent=recorded_unit_intent(profile,'Fahrenheit.',history)
        result=enrich_profile(profile,intent)
        self.assertEqual(result['scope']['fieldDefinitions']['temperature']['unit'],'°F')
        self.assertEqual(result['fields'][0]['context']['basis'],'user')
        for question in ('Should temperatures be displayed in Fahrenheit or Celsius?', 'Which title should I use?'):
            self.assertEqual(recorded_unit_intent(profile,'Fahrenheit.',[{'role':'assistant','text':question}]),'Fahrenheit.')
        self.assertEqual(recorded_unit_intent(profile,'Convert to Fahrenheit.',history),'Convert to Fahrenheit.')
        ambiguous=enrich_profile(self.profile([{'name':'temperature','numeric':True},{'name':'temp','numeric':True}]))
        self.assertEqual(recorded_unit_intent(ambiguous,'Fahrenheit.',[{'role':'assistant','text':'Are these recorded in Fahrenheit or Celsius?'}]),'Fahrenheit.')

    def test_undefined_temperature_threshold_requires_one_recorded_unit_question(self):
        profile=enrich_profile(self.profile([{'name':'temperature','numeric':True,'present':4}]))
        question,cards=recorded_unit_question(profile,'Build a monitor; ignore readings above 150.',{})
        self.assertIn('recorded in "temperature"',question);self.assertEqual(question.count('?'),1)
        self.assertEqual(len(cards),2);self.assertIn('is recorded in Fahrenheit',cards[0]['prompt'])
        defined=enrich_profile(profile,'temperature is recorded in Fahrenheit.')
        self.assertIsNone(recorded_unit_question(defined,'Build a monitor; ignore readings above 150.',{}))
        self.assertIsNone(recorded_unit_question(profile,'Show a temperature trend.',{}))
        self.assertEqual(enrich_profile(profile,recorded_unit_intent(profile,'Fahrenheit.',[{'role':'assistant','text':question}]))['scope']['fieldDefinitions']['temperature']['unit'],'°F')

    def test_confirmed_unit_turn_resumes_the_saved_goal_without_losing_original_words(self):
        from agent_service import AgentService
        from provider_service import ProviderService
        from test_agent_service import Client, Store, NewDashboardTests
        class Runtime:
            def environment(self): return {'version':'10.2.8','features':{}}
            def datasets(self): return {'indexes':[{'name':'fixture'}]}
            def preview(self, body): return {'fields':[{'name':'temperature'}],'results':[{'temperature':0}]}
        history=[{'role':'assistant','text':'Which units are recorded in "temperature": Fahrenheit, Celsius, or another unit?'}]
        client=Client([{'message':'Recorded units confirmed.','changes':[],'suggestions':[]}])
        reply=AgentService(ProviderService(Store(),client),Runtime()).assist({
            'revision':0,'definition':NewDashboardTests().blank(),'prompt':'Fahrenheit.',
            'dataContext':{'index':'fixture','earliest':'-24h'},'history':history,
            'brief':{'purpose':'Build a temperature monitor. Recorded units have not yet been confirmed.','requirements':''}})
        context=json.loads(client.calls[0]['input'][0]['content'][0]['text'])
        self.assertIn('Continue the existing dashboard goal',context['request'])
        self.assertIn('temperature is recorded in fahrenheit.',context['request'])
        self.assertEqual(context['history'],history)
        self.assertEqual(reply['dataContext']['fieldDefinitions']['temperature']['unit'],'°F')

    def test_explicit_existing_dashboard_unit_confirmation_needs_no_model_or_dashboard_edit(self):
        from agent_service import AgentService
        from provider_service import ProviderService
        from test_agent_service import Client, Store, STARTER
        class Runtime:
            def environment(self): return {'version':'10.2.8','features':{}}
            def datasets(self): return {'indexes':[{'name':'fixture'}]}
            def preview(self, body): return {'fields':[{'name':'response_time_ms'}],'results':[{'response_time_ms':0}]}
        doc=copy.deepcopy(STARTER);client=Client([])
        reply=AgentService(ProviderService(Store(),client),Runtime()).assist({
            'revision':0,'definition':doc,'prompt':'"response_time_ms" is recorded in milliseconds.',
            'dataContext':{'index':'fixture','earliest':'-24h'}})
        self.assertEqual(client.calls,[]);self.assertEqual(reply['changes'],[])
        self.assertEqual(reply['recovery']['modelCalls'],0)
        self.assertEqual(doc,STARTER)
        self.assertEqual(reply['dataContext']['fieldDefinitions']['response_time_ms']['unit'],'ms')
        self.assertEqual(reply['dataProfile']['fields'][0]['context']['basis'],'user')
        for prompt in ('Is milliseconds correct for response_time_ms?', 'response_time_ms is recorded in milliseconds. Add a peak.', 'Display response_time_ms in seconds.'):
            self.assertIsNone(unit_confirmation(reply['dataProfile'],prompt))
