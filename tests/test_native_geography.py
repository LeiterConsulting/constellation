"""Authored coordinates/paths, never real location data or user files."""
import base64
import copy
import json
from pathlib import Path
import unittest
from urllib.parse import quote
from test_native_shapes import frame, viz
from native_geography import inline_svg
from native_shapes import validate_shape
from native_intent import requested_types
from studio_inventory import authoring_contract
from knowledge_service import retrieve_guidance
from provider_service import ProviderError
from search_service import read_only_query
from native_creation import eligible, expand, schema_for
from authoring_actions import compile_actions
from studio_contract import apply_changes
from test_drafts_and_data import blank
from test_search_chart_actions import PROFILE
from authoring_budget import AuthoringBudget
from agent_service import SCHEMA

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 100"><path id="A" d="M10 10H100V90H10Z"/><path id="B" d="M130 10H230V90H130Z"/></svg>'


class GeographyTests(unittest.TestCase):
    def marker(self, layer=None):
        return viz('map', {'layers': [layer or {'type': 'marker', 'latitude': '> primary | seriesByName("lat")', 'longitude': '> primary | seriesByName("lon")'}]})

    def test_coordinate_ranges_finite_scalars_missing_and_zero(self):
        good = {'s': frame(['lat', 'lon'], [[0, 0], [-90, -180], [90, 180], [None, None]])}
        before = copy.deepcopy(good); validate_shape(self.marker(), good); self.assertEqual(good, before)
        for row in ([91, 2], [1, -181], ['private_value', 1], [float('inf'), 1], [1, ['2']], [False, 1]):
            with self.subTest(row_type=type(row[0]).__name__):
                with self.assertRaises(ProviderError) as error: validate_shape(self.marker(), {'s': frame(['lat', 'lon'], [row])})
                self.assertNotIn('private_value', str(error.exception))
        validate_shape(self.marker(), {'s': frame([], [])})

    def test_nested_default_fields_layer_isolation_and_negative_size(self):
        item = self.marker({'type': 'bubble', 'bubbleSize': '> primary | seriesByName("n")'})
        outputs={'s': frame(['latitude', 'longitude', 'n'], [[10, 20, 0]])}
        validate_shape(item, outputs)
        outputs['s']['results'][0]['n']=-1
        with self.assertRaisesRegex(ProviderError, 'nonnegative'): validate_shape(item, outputs)
        item['options']['layers'][0]['latitude']='latitude'
        with self.assertRaisesRegex(ProviderError, 'source selector'): validate_shape(item, outputs)

    def test_native_choropleth_layers_allow_signed_values_and_preserve_derived_bindings(self):
        item = self.marker({'type': 'choropleth', 'source': 'geo://default/world',
                            'areaIds': '> primary | seriesByName("region")', 'areaValues': '> primary | seriesByName("delta")'})
        validate_shape(item, {'s': frame(['region', 'delta'], [['Canada', -2], ['France', None]])})
        item['options']['layers'][0]['areaValues']='> context | customDerived()'
        validate_shape(item, {'s': frame(['region', 'delta'], [['Canada', 'unverified']])})

    def test_svg_ids_literal_data_uris_no_network_and_no_mutation(self):
        for svg in (SVG, 'data:image/svg+xml,'+quote(SVG), 'data:image/svg+xml;base64,'+base64.b64encode(SVG.encode()).decode()):
            item = viz('choropleth.svg', {'svg': svg, 'areaIds': '> primary | seriesByName("region")', 'areaValues': '> primary | seriesByName("load")'})
            outputs={'s': frame(['region', 'load'], [['A', 0], ['B', None], ['unmapped', 4]])}
            before=copy.deepcopy(item);validate_shape(item,outputs);self.assertEqual(item,before)
            outputs['s']=frame(['region','load'],[['unmapped',5]])
            with self.assertRaisesRegex(ProviderError, 'matches an SVG path'): validate_shape(item,outputs)
        self.assertIsNone(inline_svg('splunk-enterprise-kvstore://existing-asset'))
        self.assertIsNone(inline_svg('https://example.com/floor.svg'))

    def test_svg_invalid_paths_entities_and_encoding_are_bounded(self):
        for value in ('<!DOCTYPE svg [<!ENTITY a "x">]><svg>&a;</svg>', '<html/>', '<svg>',
                      'data:image/svg+xml;base64,%%', '<svg>'+' '*256000+'</svg>'):
            with self.assertRaises(ProviderError): inline_svg(value)
        for value in ('<svg><rect id="A"/></svg>', '<svg><path id="A" d="M0 0"/><path id="A" d="M1 1"/></svg>'):
            with self.assertRaisesRegex(ProviderError, 'unique IDs'):
                validate_shape(viz('choropleth.svg', {'svg':value}),{'s':frame([],[])})

    def test_unrelated_imported_asset_without_a_checked_source_stays_unchanged(self):
        item=viz('choropleth.svg',{'svg':'<legacy native asset with unknown syntax','future':{'keep':True}})
        before=copy.deepcopy(item)
        validate_shape(item,{'unrelated_source':frame(['count'],[[2]])})
        self.assertEqual(item,before)

    def test_geographic_contracts_reach_native_authoring_without_small_chart_substitutions(self):
        self.assertEqual(requested_types('Create a marker map and a choropleth SVG.'), {'splunk.map', 'splunk.choropleth.svg'})
        self.assertEqual(requested_types('Create a tree map.'), {'splunk.treemap'})
        context=authoring_contract('Create a geographic marker map',{}, {'version':'10.4.4'})
        contract=context['relevantOptions']['splunk.map'];self.assertIn('layers',contract['optionShapes']);self.assertIn('dataContract',contract)
        self.assertLess(len(json.dumps(context)),17000)
        guides=retrieve_guidance('Build a geographic marker map',{}, {'version':'10.4.4'})
        self.assertIn('geographic-layers',[g['id']for g in guides])

    def test_portable_geographic_cases(self):
        cases=json.loads((Path(__file__).parent/'fixtures/native_geography.json').read_text())['cases']
        self.assertEqual(len(cases),4)
        for case in cases:
            source=case['source'];validate_shape(viz(case['type'].removeprefix('splunk.'),case['options']),{'s':frame(source['fields'],source['rows'])})

    def test_native_geographic_read_transforms_keep_write_macro_and_time_guards(self):
        for suffix in ('iplocation clientip', 'geostats latfield=lat longfield=lon count',
                       'geom geo_countries featureIdField=country'):
            self.assertIn(suffix,read_only_query('search index=fixture | '+suffix))
            for tail in (' | outputlookup stolen.csv', ' | collect index=other', ' | rest /services/storage/passwords',
                         ' | eval x=`macro`', ' | search earliest=-30d'):
                with self.assertRaises(ProviderError):read_only_query('search index=fixture | '+suffix+tail)

    def test_geographic_plan_owns_only_new_bindings_assets_and_layout(self):
        prompt='Create exactly two pages with exactly two visualizations: a marker map and a choropleth SVG. Use this supplied SVG: '+SVG+' Give SVG areas native data-driven colors. Hide the map base layer. No tables, invented locations, uploads, extra panels or inputs.'
        context={'request':prompt,'dataProfile':PROFILE}
        original=blank()['definition'];before=copy.deepcopy(original)
        self.assertTrue(eligible(context,original))
        plan={'op':'nativeCompose','title':'Places','description':'Synthetic fixture','pages':[
            {'id':'locations','label':'Locations','purpose':'Locations','panels':[{'id':'map','type':'splunk.map','title':'Locations','pipeline':'| table lat lon', 'bindings':{'latitude':'lat','longitude':'lon','bubbleSize':''}}]},
            {'id':'floor','label':'Floor plan','purpose':'Zones','panels':[{'id':'floor','type':'splunk.choropleth.svg','title':'Zones','pipeline':'| stats sum(load) AS load BY region','bindings':{'areaIds':'region','areaValues':'load'}}]}]}
        actions=expand([plan],original,PROFILE,prompt);doc=apply_changes(original,compile_actions(original,actions,PROFILE))
        self.assertEqual(original,before)
        self.assertEqual(doc['visualizations']['map']['options'],{'layers':[{'type':'marker','latitude':'> primary | seriesByName("lat")','longitude':'> primary | seriesByName("lon")'}],'showBaseLayer':False})
        self.assertEqual(doc['visualizations']['floor']['options']['svg'],SVG)
        self.assertIn('context',doc['visualizations']['floor'])
        variants=schema_for(prompt,True)['properties']['panels']['items']['anyOf']
        self.assertEqual({v['properties']['type']['enum'][0]for v in variants},{'splunk.map','splunk.choropleth.svg'})
        for suffix in (' Set colors to red and green.', ' Add a dropdown.', ' Reuse the existing image.'):
            self.assertFalse(eligible(dict(context,request=prompt+suffix),original))
        self.assertFalse(eligible(dict(context,request=prompt.replace(SVG,'an existing image')),original))
        self.assertFalse(eligible(dict(context,request=prompt.replace('marker map','choropleth map')),original))
        self.assertFalse(eligible(context,dict(original,visualizations={'old':{'type':'splunk.table'}})))

    def test_geographic_plan_rejects_missing_size_and_asset_ambiguity(self):
        prompt='Create one page with exactly one visualization: a bubble map.'
        original=blank()['definition']
        plan={'op':'nativeCompose','title':'Locations','description':'','pages':[{'id':'places','label':'Locations','purpose':'','panels':[
            {'id':'map','type':'splunk.map','title':'Volume','pipeline':'| table lat lon n','bindings':{'latitude':'lat','longitude':'lon','bubbleSize':''}}]}]}
        with self.assertRaisesRegex(ProviderError,'bubbleSize'):expand([plan],original,PROFILE,prompt)
        plan['pages'][0]['panels'][0]['bindings']['bubbleSize']='n'
        actions=expand([plan],original,PROFILE,prompt)
        item=json.loads(next(a['value']for a in actions if a.get('path')=='/visualizations/map'))
        self.assertEqual(item['options']['layers'][0]['type'],'bubble')
        self.assertNotIn('showBaseLayer',item['options'])
        self.assertFalse(eligible({'request':'Create one page with exactly 1 visualization: a choropleth SVG. '+SVG+SVG,'dataProfile':PROFILE},original))

    def test_supplied_data_uri_is_preserved_and_all_providers_use_the_native_plan(self):
        from native_creation import supplied_svg
        for asset in ('data:image/svg+xml,'+quote(SVG,safe=''),
                      'data:image/svg+xml;base64,'+base64.b64encode(SVG.encode()).decode()):
            prompt='Create exactly two pages with exactly two visualizations: a marker map and a choropleth SVG. Use this supplied SVG: '+asset+' Give areas native data-driven colors. Hide the map base layer. No extra panels or inputs.'
            self.assertEqual(supplied_svg(prompt),asset)
            context={'request':prompt,'dataProfile':PROFILE,'canvasState':'blank','history':[],
                     'nativeAuthoring':authoring_contract(prompt,{}, {'version':'10.4.4'}),'modelLimits':{'contextTokens':32768}}
            for provider in ('openai','ollama','aitk'):
                budget=AuthoringBudget({'provider':provider},context)
                request={'instructions':'Fixture','text':{'format':{'schema':copy.deepcopy(SCHEMA)}},'input':[{'content':[{'type':'input_text','text':'Fixture'}]}]}
                budget.prepare(request,blank()['definition']);self.assertTrue(budget.native_plan)
                self.assertLess(request['max_output_tokens'],5000)
                self.assertEqual(request['text']['format']['schema']['properties']['changes']['items']['properties']['op']['enum'],['nativeCompose'])
                wire=json.loads(request['input'][0]['content'][0]['text'])
                self.assertTrue(wire['dataProfile']['baseQueryManagedByServer']);self.assertNotIn('baseQuery',wire['dataProfile'])
                self.assertIn('baseQuery',budget.context['dataProfile'])
                budget.feedback(request,{'recoveryFeedback':{'dataProfile':PROFILE,'editsApplyTo':'original'},'rejectedOutput':'untrusted'})
                repair=json.loads(request['input'][1]['content'][0]['text'])
                self.assertNotIn('baseQuery',repair['recoveryFeedback']['dataProfile'])
        self.assertIsNone(supplied_svg('Use https://example.com/floor.svg'))
        self.assertIsNone(supplied_svg('Use <svg broken>'))
