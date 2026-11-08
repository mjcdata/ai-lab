// One immutable snapshot per page session: mode changes cannot mix generations.
let snapshotPromise;
async function json(url, signal) {
  const response = await fetch(url, { signal });
  if (!response.ok) throw new Error(`Snapshot data unavailable (${response.status}). Please retry or refresh.`);
  return response.json();
}
async function snapshot() {
  if (!snapshotPromise) {
    snapshotPromise = (async () => {
      const current = await json('/snapshots/current.json');
      if (!/^[a-f0-9]{32}$/.test(current.snapshot_id)) throw new Error('Invalid snapshot version.');
      const base = `/snapshots/releases/${current.snapshot_id}`;
      const manifest = await json(`${base}/manifest.json`);
      if (manifest.schema_version !== 1 || manifest.snapshot_id !== current.snapshot_id || manifest.season !== '2024-25') throw new Error('Unsupported snapshot metadata.');
      const players = await json(`${base}/players.json`);
      if (!Array.isArray(players) || players.length !== manifest.player_count) throw new Error('Invalid player index.');
      return { base, manifest, players };
    })().catch(error => { snapshotPromise = undefined; throw error; });
  }
  return snapshotPromise;
}
export async function searchPlayers(query, signal) {
  const { players } = await snapshot();
  signal?.throwIfAborted();
  const needle = query.trim().toLocaleLowerCase('en-US');
  const matches = players.filter(p => p.name.toLocaleLowerCase('en-US').includes(needle) || p.player_id.includes(needle));
  return { players: matches.slice(0, 25), total: matches.length };
}
export async function loadComparisons(playerId, mode, signal) {
  if (!/^\d+$/.test(playerId) || !['per36', 'per_game'].includes(mode)) throw new Error('Invalid player or mode.');
  const { base, manifest, players } = await snapshot();
  signal?.throwIfAborted();
  if (!players.some(p => p.player_id === playerId)) throw new Error('Player not found in this snapshot.');
  const result = await json(`${base}/results/${mode}/${playerId}.json`, signal);
  if (result.reference?.PLAYER_ID !== playerId || result.mode !== mode || result.season !== manifest.season) throw new Error('Snapshot result identity mismatch.');
  return result;
}
