// Local packaging only. Never invokes Vercel, uploads, acquires data or scores.
import { readdir, readFile, mkdir, mkdtemp, cp, rm, rename, writeFile } from 'node:fs/promises';
import { join, resolve, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { prepareSnapshot } from './prepare-snapshot.mjs';
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
async function files(root, prefix='') {
  const result=[];
  for (const entry of await readdir(join(root,prefix),{withFileTypes:true})) {
    const path=prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isSymbolicLink()) throw new Error(`Symlink forbidden: ${path}`);
    if (entry.isDirectory()) result.push(...await files(root,path));
    else if (entry.isFile()) result.push(path);
    else throw new Error(`Nonregular file forbidden: ${path}`);
  }
  return result;
}
export async function prepareVercel(source, destination) {
  source=resolve(source);destination=resolve(destination);
  if (!relative(source,destination).startsWith('..') || !relative(destination,source).startsWith('..')) throw new Error('Bundle and export must be separate directories');
  const parent=resolve(destination,'..');await mkdir(parent,{recursive:true});
  const stage=await mkdtemp(join(parent,'.vercel-stage-'));
  try {
    // Reuse checksum/inventory validation; copy only the active snapshot.
    const manifest=await prepareSnapshot(join(source,'snapshots'),join(stage,'audit'));
    const release=`snapshots/releases/${manifest.snapshot_id}`;
    const snapshotPaths=new Set(['snapshots/current.json',`${release}/manifest.json`,...Object.keys(manifest.files).map(p=>`${release}/${p}`)]);
    const inventory=await files(source);
    const output=join(stage,'.vercel/output');const publicDir=join(output,'static');
    const checksums={};let bytes=0;
    for (const path of inventory) {
      const generated=path==='LICENSE.txt' || /^(?:index|404|_not-found)\.(?:html|txt)$/.test(path) || /^(?:_not-found\/)?__next[^/]*\.txt$/.test(path) || /^_next\/static\/[A-Za-z0-9_./-]+\.(?:js|css|woff2?|ttf|svg|png|jpg|webp|ico)$/.test(path);
      if (path.split('/').some(p=>p.startsWith('.')) || (!snapshotPaths.has(path) && !generated)) throw new Error(`Unexpected public file: ${path}`);
      const payload=await readFile(join(source,path));const text=payload.toString('utf8');
      if (/-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-proj-[A-Za-z0-9_-]{20,}|\/Users\/[^/\s]+\/|\/private\/tmp\//.test(text)) throw new Error(`Private material detected in ${path}`);
      await mkdir(join(publicDir,path,'..'),{recursive:true});await cp(join(source,path),join(publicDir,path));
      if (hash(await readFile(join(publicDir,path)))!==hash(payload)) throw new Error('Export changed while copying');
      checksums[path]=hash(payload);bytes+=payload.length;
    }
    for(const path of ['index.html','404.html',...snapshotPaths]) if(!checksums[path]) throw new Error(`Missing public file: ${path}`);
    // Confirm the export's source snapshot was not activated/changed mid-copy.
    const pointer=JSON.parse(await readFile(join(publicDir,'snapshots/current.json')));
    if(pointer.snapshot_id!==manifest.snapshot_id || hash(await readFile(join(publicDir,`${release}/manifest.json`)))!==pointer.manifest_sha256) throw new Error('Snapshot changed during packaging');
    for(const [path,info] of Object.entries(manifest.files)) if(checksums[`${release}/${path}`]!==info.sha256) throw new Error('Snapshot changed during packaging');
    await writeFile(join(output,'config.json'),JSON.stringify({version:3,routes:[{handle:'filesystem'},{src:'/.*',status:404,dest:'/404.html'}]},null,2)+'\n');
    await rm(join(stage,'audit'),{recursive:true});
    // Avoid overwriting a linked project or previous reviewed upload bundle.
    await rename(stage,destination);
    return {directory:destination,files:inventory.length,bytes,snapshot_id:manifest.snapshot_id,players:manifest.player_count};
  } finally {await rm(stage,{recursive:true,force:true});}
}
if(process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  if(!process.argv[2]) throw new Error('Provide a new isolated output directory');
  console.log(JSON.stringify(await prepareVercel(resolve('out'),process.argv[2]),null,2));
}
