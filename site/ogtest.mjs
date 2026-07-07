import sharp from 'sharp';

const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="200">
  <rect width="600" height="200" fill="#100f0f"/>
  <text x="40" y="90" font-family="Helvetica, Arial, sans-serif" font-size="44" font-weight="600" fill="#cecdc3">Two machines on one wire</text>
  <text x="40" y="140" font-family="Menlo, monospace" font-size="22" fill="#3aa99f">ACT II</text>
</svg>`;

const buf = await sharp(Buffer.from(svg)).png().toBuffer();
const { width, height } = await sharp(buf).metadata();
console.log('rendered', width, 'x', height);

const { data, info } = await sharp(buf).raw().toBuffer({ resolveWithObject: true });
let nonbg = 0;
for (let i = 0; i < data.length; i += info.channels) {
  if (Math.abs(data[i] - 0x10) > 12) nonbg++;
}
console.log('non-background pixels:', nonbg, nonbg > 3000 ? '=> TEXT RENDERED' : '=> TEXT MISSING');
