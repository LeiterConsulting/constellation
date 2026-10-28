#!/usr/bin/env node
/* Development-only PNG exports. Sharp is supplied by the developer's tools;
 * neither this script nor Sharp is required by the installed Splunk app. */
const fs = require('node:fs/promises');
const path = require('node:path');
const { createHash } = require('node:crypto');
const sharp = require(process.env.CONSTELLATION_SHARP_MODULE || 'sharp');
const root = path.resolve(__dirname, '..');
const ink = '#1f2329';
const paper = '#f5f6f7';
const png = { compressionLevel: 9, adaptiveFiltering: true };

function svg(width, height, content) {
    return Buffer.from(`<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">${content}</svg>`);
}

// These are raster brand lockups, never UI labels or substitutes for theme tokens.
function text(x, y, size, color, value, weight = 400) {
    return `<text x="${x}" y="${y}" fill="${color}" font-family="Arial,Helvetica,sans-serif" font-size="${size}" font-weight="${weight}">${value}</text>`;
}

async function tintedMark(mask, size, color) {
    const alpha = await sharp(mask).resize(size, size, { fit: 'contain', background: '#00000000' })
        .ensureAlpha().extractChannel(3).raw().toBuffer();
    const { data } = await sharp({ create: { width: size, height: size, channels: 4, background: color } })
        .raw().toBuffer({ resolveWithObject: true });
    for (let i = 0; i < alpha.length; i++) data[i * 4 + 3] = alpha[i];
    return sharp(data, { raw: { width: size, height: size, channels: 4 } }).png(png).toBuffer();
}

async function exportKit(mask) {
    const brandDir = path.join(root, 'assets/branding');
    const outputDir = path.join(brandDir, 'exports');
    await fs.mkdir(outputDir, { recursive: true });
    const entries = [];
    async function save(relativePath, data, purpose, shippedInApp = false) {
        const file = path.join(root, relativePath);
        await fs.mkdir(path.dirname(file), { recursive: true });
        if (data) await fs.writeFile(file, data);
        const bytes = await fs.readFile(file);
        const { width, height, hasAlpha } = await sharp(bytes).metadata();
        entries.push({ path: relativePath, width, height, hasAlpha, purpose, shippedInApp,
            sha256: createHash('sha256').update(bytes).digest('hex') });
    }
    for (const theme of ['dark', 'light']) {
        const foreground = theme === 'dark' ? '#ffffff' : ink;
        const background = theme === 'dark' ? ink : paper;
        const secondary = theme === 'dark' ? '#c8cdd3' : '#515961';
        const generated = path.join(brandDir, `sources/banner-${theme}.png`);
        const title = svg(1600, 640,
            text(112, 282, 80, foreground, 'Constellation', 500) +
            text(116, 351, 32, foreground, 'From question to dashboard.') +
            text(116, 410, 23, secondary, 'A conversational canvas for Splunk Dashboard Studio.'));
        const banner = await sharp(generated).resize(1600, 640, { fit: 'contain', background })
            .composite([{ input: title }]).png(png).toBuffer();
        await save(`assets/branding/exports/banner-${theme}.png`, banner, 'Documentation or introductory banner; not a permanent canvas header');

        const compact = svg(1600, 400,
            `<rect width="1600" height="400" fill="${background}"/>` +
            text(100, 189, 80, foreground, 'Constellation', 500) +
            text(104, 253, 30, secondary, 'From question to dashboard.'));
        await save(`assets/branding/exports/banner-compact-${theme}.png`,
            await sharp(compact).composite([{ input: await tintedMark(mask, 250, foreground), left: 1230, top: 75 }]).png(png).toBuffer(),
            'Compact documentation or release banner');

        const lockup = svg(640, 144, text(156, 92, 56, foreground, 'Constellation', 500));
        await save(`assets/branding/exports/wordmark-${theme}.png`,
            await sharp(lockup).composite([{ input: await tintedMark(mask, 104, foreground), left: 24, top: 20 }]).png(png).toBuffer(),
            `Transparent wordmark for a ${theme} background`);

        const social = svg(1200, 630,
            `<rect width="1200" height="630" fill="${background}"/>` +
            text(76, 295, 72, foreground, 'Constellation', 500) +
            text(80, 359, 28, secondary, 'From question to dashboard.') +
            text(80, 550, 20, secondary, 'A conversational canvas for Splunk Dashboard Studio.'));
        await save(`assets/branding/exports/social-${theme}.png`,
            await sharp(social).composite([{ input: await tintedMark(mask, 284, foreground), left: 824, top: 173 }]).png(png).toBuffer(),
            'Repository social preview; upload separately, not part of the app');

        for (const size of [20, 24, 32, 48, 512]) {
            await save(`assets/branding/exports/mark-${theme}-${size}.png`, await tintedMark(mask, size, foreground),
                `Transparent brand mark for a ${theme} background; not a native sidebar icon URL`);
        }
    }
    const splash = svg(623, 350,
        `<rect width="623" height="350" fill="${paper}"/>` +
        text(38, 145, 38, ink, 'Constellation', 500) +
        text(40, 190, 21, '#515961', 'From question') +
        text(40, 219, 21, '#515961', 'to dashboard.') +
        text(40, 311, 12, '#515961', 'A conversational canvas for Splunk Dashboard Studio.'));
    await save('assets/branding/exports/listing-splash.png',
        await sharp(splash).composite([{ input: await tintedMark(mask, 154, ink), left: 425, top: 89 }]).png(png).toBuffer(),
        '623 by 350 Splunkbase splash artwork; promotional illustration, not a live screenshot');
    for (const name of ['appIcon', 'appIcon_2x', 'appIconAlt', 'appIconAlt_2x', 'appLogo', 'appLogo_2x']) {
        await save(`splunk/constellation/static/${name}.png`, null, 'Native Splunk app-branding asset', true);
    }
    await save('src/assets/constellation-mark.png', null, 'Decorative in-app title mask, bundled into the frontend', true);
    await fs.writeFile(path.join(outputDir, 'manifest.json'), JSON.stringify({ schemaVersion: 1, assets: entries }, null, 2) + '\n');
    console.log(`Exported ${entries.length} brand assets and a dimension/hash manifest.`);
}

async function main() {
    const source = path.join(root, 'assets/branding/constellation-master.png');
    const { data, info } = await sharp(source).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
    let left = info.width, top = info.height, right = -1, bottom = -1;
    for (let y = 0; y < info.height; y++) for (let x = 0; x < info.width; x++) {
        const offset = (y * info.width + x) * 4;
        const alpha = data[offset + 3];
        // Mechanical monochrome/alpha cleanup; retain the approved silhouette.
        data[offset] = data[offset + 1] = data[offset + 2] = 0;
        data[offset + 3] = alpha < 8 ? 0 : alpha > 245 ? 255 : alpha;
        if (alpha > 16) {
            left = Math.min(left, x); top = Math.min(top, y);
            right = Math.max(right, x); bottom = Math.max(bottom, y);
        }
    }
    if (right < left || bottom < top) throw new Error('The branding master has no visible alpha silhouette.');
    const mask = await sharp(data, { raw: { width: info.width, height: info.height, channels: 4 } })
        .extract({ left, top, width: right - left + 1, height: bottom - top + 1 }).png().toBuffer();
    const staticDir = path.join(root, 'splunk/constellation/static');
    const browserDir = path.join(root, 'src/assets');
    await fs.mkdir(staticDir, { recursive: true }); await fs.mkdir(browserDir, { recursive: true });
    const master = await sharp(mask).resize(448, 448, { fit: 'contain', background: '#00000000' })
        .extend({ top: 32, bottom: 32, left: 32, right: 32, background: '#00000000' }).png(png).toBuffer();
    await fs.writeFile(path.join(browserDir, 'constellation-mark.png'), master);
    for (const size of [36, 72]) {
        const padding = size / 12;
        const alpha = await sharp(mask).resize(size - 2 * padding, size - 2 * padding, { fit: 'contain', background: '#00000000' })
            .ensureAlpha().extractChannel(3).raw().toBuffer();
        const white = Buffer.alloc((size - 2 * padding) ** 2 * 4, 255);
        for (let i = 0; i < alpha.length; i++) white[4 * i + 3] = alpha[i];
        const glyph = await sharp(white, { raw: { width: size - 2 * padding, height: size - 2 * padding, channels: 4 } }).png().toBuffer();
        const plate = Buffer.from(`<svg width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg"><rect width="${size}" height="${size}" rx="${size / 5}" fill="${ink}"/></svg>`);
        const badge = await sharp(plate).composite([{ input: glyph, left: padding, top: padding }]).png(png).toBuffer();
        const suffix = size === 72 ? '_2x' : '';
        await Promise.all(['appIcon', 'appIconAlt'].map(name => fs.writeFile(path.join(staticDir, `${name}${suffix}.png`), badge)));
    }
    for (const scale of [1, 2]) {
        const badge = await fs.readFile(path.join(staticDir, scale === 1 ? 'appIcon.png' : 'appIcon_2x.png'));
        const wordmark = Buffer.from(`<svg width="${160 * scale}" height="${40 * scale}" viewBox="0 0 160 40" xmlns="http://www.w3.org/2000/svg"><rect width="160" height="40" rx="8" fill="${ink}"/><text x="44" y="26" fill="white" font-family="Arial,Helvetica,sans-serif" font-size="17" font-weight="400">Constellation</text></svg>`);
        await sharp(wordmark).composite([{ input: badge, left: 2 * scale, top: 2 * scale }]).png(png)
            .toFile(path.join(staticDir, scale === 1 ? 'appLogo.png' : 'appLogo_2x.png'));
    }
    await exportKit(mask);
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
