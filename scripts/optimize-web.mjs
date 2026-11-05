import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { dedup, meshopt, prune, textureCompress, weld } from '@gltf-transform/functions';
import { MeshoptEncoder } from 'meshoptimizer';
import sharp from 'sharp';
import fs from 'node:fs/promises';

const source = 'public/media/lamian.glb';
await MeshoptEncoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.encoder': MeshoptEncoder });
const document = await io.read(source);
const before = (await fs.stat(source)).size;
await document.transform(dedup(), prune(), weld(), textureCompress({ encoder: sharp, targetFormat: 'webp', resize: [1536, 1536] }), meshopt({ encoder: MeshoptEncoder, level: 'high' }));
await io.write(source, document);
console.log(`GLB: ${(before / 1048576).toFixed(2)} MiB -> ${((await fs.stat(source)).size / 1048576).toFixed(2)} MiB`);
