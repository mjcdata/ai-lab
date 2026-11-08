// Validate the active local snapshot, then stage only that release for static export.
import { readFile, mkdir, mkdtemp, cp, rm, rename } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
export async function prepareSnapshot(source, publicDir) {
  const currentBytes = await readFile(join(source, 'current.json'));
  const current = JSON.parse(currentBytes);
  if (!/^[a-f0-9]{32}$/.test(current.snapshot_id)) throw new Error('Invalid snapshot ID');
  const release = join(source, 'releases', current.snapshot_id);
  const manifestBytes = await readFile(join(release, 'manifest.json'));
  if (hash(manifestBytes) !== current.manifest_sha256) throw new Error('Manifest checksum mismatch');
  const manifest = JSON.parse(manifestBytes);
  if (manifest.schema_version !== 1 || manifest.snapshot_id !== current.snapshot_id || manifest.season !== '2024-25') throw new Error('Unsupported snapshot');
  const players = JSON.parse(await readFile(join(release, 'players.json')));
  const expected = ['players.json', ...manifest.modes.flatMap(mode => players.map(p => `results/${mode}/${p.player_id}.json`))];
  if (manifest.player_count !== players.length || manifest.result_count !== players.length * 2 || manifest.modes.join(',') !== 'per36,per_game' || expected.length !== Object.keys(manifest.files).length) throw new Error('Incomplete snapshot inventory');
  for (const relative of expected) {
    if (!/^(players\.json|results\/(per36|per_game)\/\d+\.json)$/.test(relative)) throw new Error('Invalid snapshot path');
    const bytes = await readFile(join(release, relative));
    const info = manifest.files[relative];
    if (!info || bytes.length !== info.bytes || hash(bytes) !== info.sha256) throw new Error(`Snapshot checksum mismatch: ${relative}`);
    JSON.parse(bytes);
  }
  // Until validation and copying succeed, existing staged assets stay untouched.
  await mkdir(publicDir, { recursive: true });
  const stage = await mkdtemp(join(publicDir, '.snapshot-stage-'));
  try {
    await mkdir(join(stage, 'releases'), { recursive: true });
    const destination = join(stage, 'releases', current.snapshot_id);
    await mkdir(destination, { recursive: true });
    await cp(join(release, 'manifest.json'), join(destination, 'manifest.json'));
    for (const relative of expected) {
      await mkdir(join(destination, relative, '..'), { recursive: true });
      await cp(join(release, relative), join(destination, relative));
      const copied = await readFile(join(destination, relative));
      if (hash(copied) !== manifest.files[relative].sha256) throw new Error('Snapshot changed during copy');
    }
    if (hash(await readFile(join(destination, 'manifest.json'))) !== current.manifest_sha256) throw new Error('Manifest changed during copy');
    await cp(join(source, 'current.json'), join(stage, 'current.json'));
    // Source activation during build must not pair a new pointer with old files.
    if (!(await readFile(join(stage, 'current.json'))).equals(currentBytes)) throw new Error('Snapshot changed during build; retry');
    await rm(join(publicDir, 'snapshots'), { recursive: true, force: true });
    await rename(stage, join(publicDir, 'snapshots'));
  } finally { await rm(stage, { recursive: true, force: true }); }
  return manifest;
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const source = resolve(process.env.NBA_SNAPSHOT_DIR || '../../artifacts/snapshots');
  const manifest = await prepareSnapshot(source, resolve('public'));
  console.log(`Validated ${manifest.result_count} results; staged snapshot ${manifest.snapshot_id}`);
}
