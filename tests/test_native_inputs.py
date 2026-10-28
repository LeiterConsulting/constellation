"""Authored input graphs and version boundaries, without credentials or inference."""
import copy
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from native_inputs import validate_input_dependencies
from studio_versions import validate_native_version
from studio_inventory import authoring_contract
from provider_service import ProviderError

class InputTests(unittest.TestCase):
    def doc(self):
        return {'inputs':{'parent':{'type':'input.dropdown','options':{'token':'parent'}},
                          'child':{'type':'input.multiselect','options':{'token':'child','isCascadingInput':True},'dataSources':{'primary':'child_source'}}},
                'dataSources':{'base':{'type':'ds.search','options':{'query':'search index="fixture" parent=$parent|s$'}},
                               'child_source':{'type':'ds.chain','options':{'extend':'base','query':'| stats count by name'}}}}
    def test_acyclic_query_and_chain_dependencies_are_supported(self):
        validate_input_dependencies(self.doc(),{})
    def test_self_and_multi_input_cycles_are_rejected(self):
        doc=self.doc();doc['dataSources']['base']['options']['query']+=' child=$child|s$'
        with self.assertRaisesRegex(ProviderError,'cycle'):validate_input_dependencies(doc,{})
        doc=self.doc();doc['inputs']['parent']['dataSources']={'primary':'parent_source'};doc['dataSources']['parent_source']={'type':'ds.search','options':{'query':'search index="fixture" child=$child|s$'}}
        with self.assertRaises(ProviderError):validate_input_dependencies(doc,{})
    def test_unchanged_imported_cycles_survive_unrelated_edits(self):
        doc=self.doc();doc['dataSources']['base']['options']['query']+=' child=$child|s$';old=copy.deepcopy(doc);doc['inputs']['parent']['title']='Clearer title'
        validate_input_dependencies(doc,old)
    def test_a_changed_cycle_on_preexisting_cyclic_nodes_is_not_grandfathered(self):
        old=self.doc();old['inputs']['parent']['dataSources']={'primary':'parent_source'};old['dataSources']['parent_source']={'type':'ds.search','options':{'query':'search index="fixture" child=$child|s$'}}
        new=copy.deepcopy(old);new['dataSources']['base']['options']['query']='search index="fixture" child=$child|s$'
        with self.assertRaises(ProviderError):validate_input_dependencies(new,old)

    def test_namespaces_are_not_conflated(self):
        doc=self.doc();doc['inputs']['child']['options']['tokenNamespace']='other';doc['dataSources']['base']['options']['query']+=' child=$child|s$'
        validate_input_dependencies(doc,{})
        doc['dataSources']['base']['options']['query']+=' child=$other:child|s$'
        with self.assertRaises(ProviderError):validate_input_dependencies(doc,{})
    def test_reset_option_requires_104_but_preserves_existing_import(self):
        item=self.doc()['inputs']['child']
        with self.assertRaises(ProviderError):validate_native_version(item,{},'10.2.8')
        validate_native_version(item,{},'10.4.4');validate_native_version(item,copy.deepcopy(item),'10.2.8')
        c=authoring_contract('dropdown and multiselect',{'visualizations':{}},{'version':'10.2.8'})
        self.assertNotIn('isCascadingInput',c['relevantInputOptions']['input.multiselect'])

class MenuActionTests(unittest.TestCase):
    def action(self, **values):
        return dict(op='menu',id='child',inputType='input.dropdown',title='Device',token='device',sourceId='choices',labelField='device',valueField='device',defaultMode='all',cascading=True,**values)
    def doc(self):
        return {'visualizations':{},'inputs':{'back':{'type':'input.button','options':{'label':'Back'},'future':{'keep':True}}},'dataSources':{'choices':{'type':'ds.search','options':{'query':'search index="fixture" | stats count by device'}}},'layout':{'globalInputs':['back'],'type':'absolute','structure':[]}}
    def test_menu_compiles_without_reconstructing_existing_inputs_or_layout(self):
        from authoring_actions import compile_actions
        from studio_contract import apply_changes
        from studio_features import validate_features
        doc=self.doc();before=copy.deepcopy(doc);changes=compile_actions(doc,[self.action()]);result=apply_changes(doc,changes)
        self.assertEqual(doc,before);self.assertEqual(result['inputs']['back'],doc['inputs']['back']);self.assertEqual(result['layout']['globalInputs'],['back','child'])
        self.assertEqual(result['dataSources'],doc['dataSources']);self.assertEqual(result['inputs']['child']['options']['defaultValue'],'*')
        validate_features(result,doc,{'version':'10.4.4'})
        with self.assertRaises(ProviderError):validate_features(result,doc,{'version':'10.2.8'})
    def test_modes_and_native_multiselect_default(self):
        from input_actions import compile_menu
        for mode in ['all','first','none']:
            action=self.action();action.update(defaultMode=mode,inputType='input.multiselect',cascading=False)
            _,item=compile_menu(action,self.doc());self.assertNotIn('isCascadingInput',item['options'])
            if mode=='all':self.assertEqual(item['options']['defaultValue'],['*'])
            elif mode=='first':self.assertTrue(item['options']['selectFirstSearchResult']);self.assertNotIn('defaultValue',item['options'])
            else:self.assertNotIn('defaultValue',item['options']);self.assertNotIn('selectFirstSearchResult',item['options'])
    def test_existing_id_token_and_duplicate_new_tokens_are_rejected(self):
        from authoring_actions import compile_actions
        doc=self.doc();a=self.action();a['id']='back'
        with self.assertRaises(ProviderError):compile_actions(doc,[a])
        a=self.action();b=dict(a,id='other')
        with self.assertRaises(ProviderError):compile_actions(doc,[a,b])
        doc['inputs']['other']={'type':'input.text','options':{'token':'device','tokenNamespace':'default'}}
        with self.assertRaises(ProviderError):compile_actions(doc,[a])
    def test_fields_cannot_inject_a_dos_expression(self):
        import json
        from input_actions import compile_menu
        a=self.action();a['valueField']='x") | objects() | seriesByName("y'
        _,item=compile_menu(a,self.doc());self.assertIn(json.dumps(a['valueField']),item['context']['value'])

class MenuIntentTests(unittest.TestCase):
    def test_partial_menu_work_does_not_satisfy_an_explicit_creation_request(self):
        from native_inputs import validate_menu_intent
        old={'inputs':{'back':{'type':'input.button'}},'dataSources':{}}
        new=copy.deepcopy(old);new['dataSources']['choices']={'type':'ds.search'}
        with self.assertRaisesRegex(ProviderError,'search source alone'):
            validate_menu_intent('Add exactly two global native dropdown inputs. Do not change any existing chart.',new,old)
        new['inputs'].update(a={'type':'input.dropdown'},b={'type':'input.dropdown'})
        validate_menu_intent('Add exactly two global native dropdown inputs. Do not change any existing chart.',new,old)
        new['inputs']['back']['type']='input.text'
        with self.assertRaisesRegex(ProviderError,'return button'):
            validate_menu_intent('Add exactly two global native dropdown inputs. Do not change any existing chart.',new,old)
    def test_ambiguous_or_unrelated_counts_do_not_become_menu_requirements(self):
        from native_inputs import validate_menu_intent
        for text in ['Add two colors to the dropdown','Rename the two dropdowns','Remove two dropdowns']:
            validate_menu_intent(text,{'inputs':{}},{'title':'Old'})

class MenuPlanTests(unittest.TestCase):
    def test_plan_is_narrow_and_preserves_unrelated_native_work(self):
        from native_inputs import additive_menu_plan, validate_additive_menus
        doc={'visualizations':{'v':{'future':[1,2]}},'inputs':{'back':{'type':'input.button'}},'dataSources':{},'layout':{'globalInputs':['back'],'future':True}}
        profile={'scope':{'language':'spl'}};prompt='Add exactly two global native dropdown inputs. Do not change any existing chart.'
        self.assertEqual(additive_menu_plan(prompt,doc,profile,[])['count'],2)
        self.assertIsNone(additive_menu_plan(prompt,doc,profile,[{'data':'fixture'}]))
        self.assertIsNone(additive_menu_plan(prompt,doc,{'scope':{'language':'spl2'}},[]))
        self.assertIsNone(additive_menu_plan('Add two dropdowns and change the charts',doc,profile,[]))
        candidate=copy.deepcopy(doc);candidate['inputs']['menu']={'type':'input.dropdown'};candidate['layout']['globalInputs'].append('menu');validate_additive_menus(candidate,doc)
        candidate['visualizations']['v']['future']=[3]
        with self.assertRaises(ProviderError):validate_additive_menus(candidate,doc)
    def test_model_context_and_repairs_remain_small_without_losing_guards(self):
        import json
        from authoring_budget import AuthoringBudget
        from agent_service import SCHEMA
        context={'request':'Add two global dropdowns. Do not change any existing chart.','canvasState':'dashboard','history':[],
                 'environment':{'version':'10.2.8'},'modelLimits':{'contextTokens':32768},'dashboardBrief':{'requirements':'Keep exclusions'},
                 'dataProfile':{'baseQuery':'search index="fixture"','scope':{'language':'spl','query':'search index="fixture"'},'fields':[{'name':'device'}]},
                 'newMenusOnly':{'count':2,'inputType':'input.dropdown','existingInputIds':['back'],'existingSourceIds':['original'],'existingTokens':[]},
                 'retrievedGuidance':[{'id':'native-inputs','text':'Keep actual-output validation.'}],'nativeAuthoring':{'unrelated':'x'*100000}}
        request={'instructions':'General authoring','max_output_tokens':5000,'text':{'format':{'schema':copy.deepcopy(SCHEMA)}},'input':[{'content':[{'type':'input_text','text':'Fixture'}]}]}
        budget=AuthoringBudget({'provider':'ollama'},context);budget.prepare(request,{'visualizations':{'v':{'future':'x'*100000}},'layout':{}})
        model=json.loads(request['input'][0]['content'][0]['text']);self.assertNotIn('definition',model);self.assertNotIn('baseQuery',model['dataProfile']);self.assertNotIn('nativeAuthoring',model)
        self.assertEqual(model['dashboardBrief']['requirements'],'Keep exclusions');self.assertEqual(model['retrievedGuidance'],context['retrievedGuidance'])
        actions=request['text']['format']['schema']['properties']['changes']['items']['anyOf'];self.assertEqual({a['properties']['op']['enum'][0]for a in actions},{'search','menu'})
        budget.feedback(request,{'recoveryFeedback':{'candidateDefinition':{'large':'x'*100000},'placementHint':'x'*100000,'dataProfile':context['dataProfile']},'rejectedOutput':'x'*100000})
        repair=json.loads(request['input'][1]['content'][0]['text']);self.assertEqual(repair['recoveryFeedback']['editsApplyTo'],'original');self.assertNotIn('candidateDefinition',repair['recoveryFeedback']);self.assertEqual(repair['rejectedOutput'],'')
