"""Offline scaler-contributor experiment. Never changes production defaults."""
import argparse
import copy
import json
import math
from pathlib import Path
from .similarity import SeasonBaseline
from .preparation import FEATURES

THRESHOLDS = (0, 50, 100, 250, 500)
EXAMPLES = ('1642355', '201939', '203999', '1642264', '1630162')


def variant(control, minimum_minutes):
    """Copy scorer, fitting only eligible latest contributors above inclusive cutoff."""
    if minimum_minutes < 0:
        raise ValueError('Minimum minutes must be nonnegative')
    scorer = copy.copy(control)
    reference = [c for c in control.latest.values() if c['cumulative_minutes'] >= minimum_minutes]
    if not reference:
        raise ValueError('No scaler contributors')
    scorer.mean = {f: math.fsum(c['per36'][f] for c in reference)/len(reference) for f in FEATURES}
    scorer.scale = {f: math.sqrt(math.fsum((c['per36'][f]-scorer.mean[f])**2
                                         for c in reference)/len(reference)) or 1.0 for f in FEATURES}
    return scorer, len(reference)


def signature(result):
    return [c['player_id'] for c in result['comparisons']]


def run(checkpoints, examples=EXAMPLES):
    control = SeasonBaseline(checkpoints)
    controls = {p: control.compare(p) for p in control.latest}
    output = {}
    for threshold in THRESHOLDS:
        scorer, count = variant(control, threshold)
        changes, overlaps, groups, examples_out = 0, [], {'under250': [], 'atleast1000': []}, {}
        for pid, original in controls.items():
            result = scorer.compare(pid)
            assert result['candidate_count'] == original['candidate_count']
            a, b = signature(original), signature(result)
            overlap = len(set(a)&set(b));overlaps.append(overlap)
            changes += a != b
            minutes = original['reference']['cumulative_minutes']
            if minutes < 250: groups['under250'].append(overlap)
            if minutes >= 1000: groups['atleast1000'].append(overlap)
            if pid in examples:
                examples_out[pid] = dict(minutes=minutes, candidates=result['candidate_count'],
                    overlap_control=overlap, matches=[dict(player_id=c['player_id'], distance=c['distance'],
                    minutes=c['checkpoint']['cumulative_minutes']) for c in result['comparisons']])
        temporal = {}
        for pid in examples:
            if pid not in control.latest: continue
            latest = control.latest[pid]
            seq = [c for c in control.checkpoints if str(c['PLAYER_ID']) == pid]
            finalset=set(signature(controls[pid] if threshold==0 else scorer.compare(pid)))
            query_scorer=copy.copy(scorer);query_scorer.latest=scorer.latest.copy()
            snapshots=[]
            for fraction in (.25,.5,.75):
                cp=min(seq,key=lambda c:(abs(c['cumulative_minutes']-fraction*latest['cumulative_minutes']),c['GAME_DATE'],c['GAME_ID']))
                query_scorer.latest[pid]=cp
                result=query_scorer.compare(pid)
                snapshots.append(dict(minutes=cp['cumulative_minutes'],overlap_final=len(finalset&set(signature(result))),
                                      matches=signature(result),candidates=result['candidate_count']))
            temporal[pid]=snapshots
        output[threshold]=dict(contributors=count,mean=scorer.mean,scale=scorer.scale,
                              changed_ordered_lists=changes,mean_top5_overlap=sum(overlaps)/len(overlaps),
                              groups={k:dict(players=len(v),mean_overlap=sum(v)/len(v)) for k,v in groups.items()},
                              examples=examples_out,temporal=temporal)
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoints',type=Path,default=Path('data/derived/2024-25.json'))
    parser.add_argument('--output',type=Path,default=Path('artifacts/scaler_experiment.json'))
    args=parser.parse_args()
    output=run(json.loads(args.checkpoints.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
    print(f'Wrote isolated experiment results to {args.output}')


if __name__=='__main__': main()
