/** Passive SVG subset, shared by upload, native preview and portable import.
 * Reject unsupported markup rather than silently changing the user's artwork. */
export function validateSvg(text: string): string {
  if (!text || new TextEncoder().encode(text).length > 500_000 || /<!|<\?(?!xml\s)/i.test(text)) throw new Error('Use a passive SVG under 500 KB, without entities, scripts or external resources.');
  const doc = new DOMParser().parseFromString(text, 'image/svg+xml');
  if (doc.getElementsByTagName('parsererror').length || doc.documentElement.localName !== 'svg') throw new Error('This file is not a valid SVG.');
  const tags = new Set('svg g path rect circle ellipse line polyline polygon title desc defs clipPath linearGradient radialGradient stop use symbol'.split(' '));
  const attrs = new Set('id viewBox width height x y x1 y1 x2 y2 cx cy r rx ry d points transform fill stroke stroke-width stroke-linecap stroke-linejoin stroke-miterlimit stroke-dasharray stroke-dashoffset fill-rule clip-rule opacity fill-opacity stroke-opacity clip-path offset stop-color stop-opacity gradientUnits gradientTransform spreadMethod preserveAspectRatio version role aria-label'.split(' '));
  let count = 0;
  const visit = (element: Element, depth: number) => {
    if (++count > 5000 || depth > 40 || element.namespaceURI !== 'http://www.w3.org/2000/svg' || !tags.has(element.localName)) throw new Error('This SVG contains unsupported markup. Use paths, shapes and local gradients.');
    for (const attr of Array.from(element.attributes)) {
      if (attr.name === 'xmlns' && attr.value === 'http://www.w3.org/2000/svg') continue;
      if (attr.name === 'xmlns:xlink' && attr.value === 'http://www.w3.org/1999/xlink') continue;
      if (['href','xlink:href'].includes(attr.name) && element.localName === 'use' && /^#[A-Za-z_][\w.-]*$/.test(attr.value)) continue;
      if (attr.namespaceURI || !attrs.has(attr.name) || /[<>\\]|(?:javascript|data|https?):|\/\/|@|&/i.test(attr.value) || /url\s*\(/i.test(attr.value) && !/^url\(#[A-Za-z_][\w.-]*\)$/.test(attr.value)) throw new Error('This SVG contains unsupported attributes or external resources. Export a passive SVG with presentation attributes.');
    }
    Array.from(element.childNodes).filter(child => child.nodeType === 1).forEach(child => visit(child as Element, depth + 1));
  };
  visit(doc.documentElement, 0);
  return text;
}

export function svgDataUri(text: string): string {
  validateSvg(text);
  return 'data:image/svg+xml;base64,' + btoa(Array.from(new TextEncoder().encode(text), byte => String.fromCharCode(byte)).join(''));
}
export function svgText(dataURI: string): string {
  if (!dataURI.startsWith('data:image/svg+xml;base64,')) throw new Error('Choose an SVG for a choropleth map.');
  const text = new TextDecoder('utf-8',{fatal:true}).decode(Uint8Array.from(atob(dataURI.split(',')[1]),c=>c.charCodeAt(0)));
  validateSvg(text);return text;
}
export function svgAreaIds(dataURI: string): string[] {
  const text=svgText(dataURI);if(new TextEncoder().encode(text).length>256_000)throw new Error('Use a choropleth SVG under 250 KB.');
  const doc = new DOMParser().parseFromString(text,'image/svg+xml');
  const paths=Array.from(doc.getElementsByTagName('path')).filter(path=>path.getAttribute('d'));
  const ids=paths.map(path=>path.getAttribute('id') || '');
  if (!ids.length || ids.some(id=>!id || id.length>200) || new Set(ids).size!==ids.length) throw new Error('A choropleth SVG needs a unique ID on every path with a d outline.');
  return ids;
}
export function validateAssetData(dataURI: string, kind: 'image' | 'icon'): string {
  const match = /^data:image\/(png|jpeg|gif|webp|svg\+xml);base64,([A-Za-z0-9+/]+={0,2})$/.exec(dataURI);
  if (!match || dataURI.length > 5_400_000 || match[2].length % 4 !== 0) throw new Error('Unsupported or oversized Studio asset.');
  let raw: string;
  try { raw = atob(match[2]); } catch { throw new Error('Invalid asset encoding.'); }
  if (btoa(raw) !== match[2] || raw.length > 4_000_000) throw new Error('Invalid or oversized asset encoding.');
  if (match[1] === 'svg+xml') {
    validateSvg(new TextDecoder('utf-8', { fatal: true }).decode(Uint8Array.from(raw, c => c.charCodeAt(0))));
  } else {
    if (kind === 'icon') throw new Error('Studio icons must be SVG files.');
    const bytes = Array.from(raw.slice(0,16), c => c.charCodeAt(0));
    const valid = match[1] === 'png' ? [137,80,78,71,13,10,26,10].every((n,i) => bytes[i] === n)
      : match[1] === 'jpeg' ? bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255
      : match[1] === 'gif' ? ['GIF87a','GIF89a'].includes(raw.slice(0,6)) : match[1] === 'webp' && raw.slice(0,4) === 'RIFF' && raw.slice(8,12) === 'WEBP';
    if (!valid) throw new Error('The asset contents do not match its image type.');
  }
  return dataURI;
}
