import type { StudioDefinition } from './document';
export const assetType = 'splunk-enterprise-kvstore';
export const isNativeImage = (value: string) => new RegExp(`^${assetType}://[A-Za-z0-9_-]{1,128}$`).test(value);
export const isPackagedImage = (value: string) => /^\/(?:[a-z]{2}-[A-Z]{2}\/)?static\/app\/[A-Za-z0-9_-]+\/(?:[A-Za-z0-9_-]+\/)*[A-Za-z0-9_-]+\.(?:png|jpe?g|webp|gif|svg)$/i.test(value);
export const previewImage = (value: string) => isNativeImage(value) || isPackagedImage(value);
export const hasSharedImages = (definition: StudioDefinition) => JSON.stringify(definition).includes(`${assetType}://`);
