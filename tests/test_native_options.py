import copy
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from native_options import validate_options, matches
from studio_inventory import INVENTORY
from studio_features import validate_features
from provider_service import ProviderError


class NativeOptionTests(unittest.TestCase):
    def test_each_embedded_type_accepts_native_bindings_and_preserves_unknown_work(self):
        for kind, contract in INVENTORY['visualizations'].items():
            with self.subTest(kind=kind):
                self.assertTrue(contract['options'])
                option = next(iter(contract['options']))
                item = {'type': kind, 'options': {option: '> primary | seriesByName("fixture")', 'futureNativeProperty': {'retain': [1, 2]}}}
                before = copy.deepcopy(item)
                validate_options(item, {})
                self.assertEqual(item, before)
        self.assertEqual(len(INVENTORY['visualizations']), 29)

    def test_wrong_literal_container_is_rejected_for_each_embedded_type(self):
        for kind, contract in INVENTORY['visualizations'].items():
            # Background styling is scalar across these renderer types. Others
            # use an explicit scalar option from their committed contract.
            option = next((name for name in ('backgroundColor', 'src', 'stroke', 'markdown', 'fillColor') if name in contract['options']), None)
            if not option: continue
            with self.subTest(kind=kind, option=option), self.assertRaises(ProviderError):
                validate_options({'type': kind, 'options': {option: {'invalid': True}}}, {})

    def test_native_literal_and_dynamic_shapes_and_nested_preservation(self):
        validate_options({'type': 'splunk.line', 'options': {'legendDisplay': 'bottom', 'seriesColors': ['#336699', '#773366']}}, {})
        for value in ([42], {'fake': 'color'}, False):
            with self.assertRaises(ProviderError): validate_options({'type': 'splunk.line', 'options': {'seriesColors': value}}, {})
        rule = {'type': 'object', 'properties': {'unchanged': {'type': 'number'}, 'changed': {'type': 'number'}}}
        self.assertTrue(matches({'unchanged': 'futureBinding', 'changed': 2}, rule, {'unchanged': 'futureBinding', 'changed': 1}))
        self.assertFalse(matches({'changed': 'incorrect'}, rule, {}))
        self.assertFalse(matches(10 ** 500, {'type': 'number'}))
        self.assertFalse(matches(True, {'type': 'number'}))

    def test_imported_invalid_known_values_survive_unrelated_edits(self):
        before = {'type': 'splunk.line', 'options': {'seriesColors': {'future': True}}}
        changed = copy.deepcopy(before); changed['title'] = 'New title'
        validate_options(changed, before)
        changed['options']['seriesColors'] = {'invalid': 'new'}
        with self.assertRaises(ProviderError): validate_options(changed, before)

    def test_input_default_contract_flags_are_not_literal_schemas(self):
        for kind in ('input.dropdown', 'input.multiselect', 'input.text', 'input.number'):
            with self.subTest(kind=kind):
                validate_options({'type': kind, 'options': {'token': 'fixture', 'defaultValue': 'A'}}, {})
        with self.assertRaises(ProviderError):
            validate_options({'type': 'input.dropdown', 'options': {'items': [{'label': 'A', 'value': 7}]}}, {})

    def test_full_feature_validation_applies_option_shapes_atomically(self):
        doc = {'layout': {}, 'visualizations': {'line': {'type': 'splunk.line', 'options': {'seriesColors': ['#336699']}}}}
        original = copy.deepcopy(doc)
        changed = copy.deepcopy(doc); changed['visualizations']['line']['options']['seriesColors'] = [True]
        with self.assertRaises(ProviderError): validate_features(changed, doc, {'version': '10.4'})
        self.assertEqual(doc, original)

    def test_unset_handler_requires_native_104_and_preserves_older_imports(self):
        doc = {'layout': {}, 'visualizations': {}, 'inputs': {'clear': {'type': 'input.button', 'options': {'label': 'Clear'},
               'eventHandlers': [{'type': 'drilldown.unsetTokens', 'options': {'tokenNames': ['choice']}}]}}}
        with self.assertRaises(ProviderError) as error: validate_features(doc, {}, {'version': '10.2.8'})
        self.assertEqual(error.exception.code, 'native_handler_version')
        validate_features(doc, {}, {'version': '10.4.4'})
        changed = copy.deepcopy(doc); changed['inputs']['clear']['options']['label'] = 'Clear selection'
        validate_features(changed, doc, {'version': '10.2.8'})
