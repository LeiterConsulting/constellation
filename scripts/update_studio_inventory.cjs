/* Rebuild structural option metadata from the pinned renderer. No vendor prose,
 * implementation, user definitions or runtime data enters this inventory. */
const fs = require('node:fs');
const path = require('node:path');
const base = path.dirname(require.resolve('@splunk/dashboard-presets/package.json'));
const dir = path.join(base, 'node_modules/@splunk/visualizations');
const target = path.join(__dirname, '../splunk/constellation/bin/contracts/studio_inventory.json');
const presetSource = fs.readFileSync(path.join(base, 'EnterprisePreset.js'), 'utf8');
const presetViz = new Set([...presetSource.matchAll(/require\("@splunk\/visualizations\/([^"/]+)"\)/g)].map(match => match[1]));
const allowed = new Set(['type', 'enum', 'minimum', 'maximum', 'minItems', 'maxItems', 'properties', 'patternProperties', 'items', 'anyOf', 'oneOf']);
function shape(value) {
  if (Array.isArray(value)) return value.map(shape);
  if (!value || typeof value !== 'object') return value;
  const result = {};
  for (const [key, child] of Object.entries(value)) {
    if (!allowed.has(key)) continue;
    result[key] = key === 'properties' || key === 'patternProperties'
      ? Object.fromEntries(Object.entries(child).map(([name, rule]) => [name, shape(rule)])) : shape(child);
  }
  // Bindings are useful structural examples; omit prose and cosmetic defaults.
  if (typeof value.default === 'string' && value.default.startsWith('>')) result.binding = value.default;
  return result;
}
const visualizations = {};
for (const file of fs.readdirSync(dir).filter(name => name.endsWith('.config.js')).sort()) {
  const config = require(path.join(dir, file)).default;
  if (!presetViz.has(file.replace('.config.js', ''))) continue;
  visualizations[config.key] = {
    minimumEnterprise: config.key === 'splunk.networkGraph' ? '10.4' : '10.0',
    options: Object.fromEntries(Object.entries(config.optionsSchema).map(([name, rule]) => [name, shape(rule)])),
    events: Object.keys(config.events || {}),
    requiredSources: (config.dataContract?.requiredDataSources || []).map(source => source.name),
  };
}
// This decorative asset belongs to dashboard-layouts rather than visualizations.
const lineOptions = require('@splunk/dashboard-layouts/visualizations/ConnectedLineOptionsSchema').default;
const lineSource = fs.readFileSync(require.resolve('@splunk/dashboard-layouts/visualizations/ConnectedLine'), 'utf8');
const lineKey = /^  key: "([^"]+)"/m.exec(lineSource)?.[1];
if (lineKey !== 'abslayout.line') throw new Error('Review the native connector contract after this dependency update.');
visualizations[lineKey] = { minimumEnterprise: '10.0',
  options: Object.fromEntries(Object.entries(lineOptions).map(([name, rule]) => [name, shape(rule)])), events: [], requiredSources: [] };
const inputOptions = {};
for (const [type, module] of Object.entries({
  'input.dropdown': 'Select/SelectSchema', 'input.multiselect': 'Multiselect/MultiselectSchema',
  'input.text': 'Text/TextSchema', 'input.number': 'Number/NumberSchema',
})) {
  const options = require('@splunk/dashboard-inputs/' + module).default;
  const flat = options.extend ? Object.assign({}, ...options.extend.anyOf.map(branch => branch.properties)) : options;
  inputOptions[type] = Object.fromEntries(Object.entries(flat).map(([name, rule]) => [name, shape(rule)]));
}
const inventory = {
  schemaVersion: 1,
  rendererPackage: '@splunk/dashboard-presets', rendererVersion: require(path.join(base, 'package.json')).version,
  source: 'https://splunkui.splunk.com/Packages/dashboard-presets',
  qualification: 'Structural inventory of the pinned embedded renderer. Version minima are the app baseline, not complete native or future-release qualification.',
  visualizations,
  inputs: ['input.dropdown', 'input.multiselect', 'input.text', 'input.number', 'input.timerange', 'input.button'],
  inputOptions,
  dataSources: ['ds.search', 'ds.chain', 'ds.savedSearch', 'ds.test', 'ds.spl2', 'ds.spl2.view'],
  eventHandlers: ['drilldown.customUrl', 'drilldown.setToken', 'drilldown.setTimeRange', 'drilldown.switchToTab', 'drilldown.resetTokens', 'drilldown.unsetTokens'],
  layouts: ['absolute', 'grid'],
};
const output = JSON.stringify(inventory, null, 2) + '\n';
if (process.argv.includes('--check')) {
  if (fs.readFileSync(target, 'utf8') !== output) throw new Error('Studio inventory differs from pinned dependencies. Run node scripts/update_studio_inventory.cjs and review changes.');
} else fs.writeFileSync(target, output);
console.log(`${Object.keys(visualizations).length} visualization contracts; ${Buffer.byteLength(output)} bytes`);
