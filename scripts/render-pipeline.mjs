// Bright re-render pipeline: refine → final stills → update web media.
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';

const BLENDER = 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe';
const log = fs.openSync('render-pipeline.log', 'a');
const run = (args) => new Promise((ok, bad) => {
  const p = spawn(BLENDER, args, { stdio: ['ignore', log, log] });
  p.on('exit', (c) => c === 0 ? ok() : bad(new Error('exit ' + c)));
});

await run(['--background', 'output/Lamian_Reconstruction.blend', '--threads', '16', '--python', 'scripts/refine_scene.py']);
console.log('refine done');
await run(['--background', 'output/Lamian_Reconstruction_Refined.blend', '--threads', '16', '--python', 'scripts/render_refined_preview.py', '--', '--final']);
console.log('final renders done');
spawnSync('python', ['-c', `
from PIL import Image
from pathlib import Path
import shutil
p=Path('public/media')
for n in ['hero','low_angle','top_detail','close_detail']:
    src=Path('output/refined')/(n+'.png');shutil.copyfile(src,p/(n+'.png'))
    im=Image.open(src).convert('RGB');im.thumbnail((1600,1400));im.save(p/(n+'.webp'),quality=90)
print('webp updated')`], { stdio: ['ignore', log, log] });
fs.writeFileSync('render-pipeline.done', new Date().toISOString());
console.log('pipeline complete');
