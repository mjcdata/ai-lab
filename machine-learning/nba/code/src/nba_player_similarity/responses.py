"""Shared read-only response decoration for the API and static snapshots."""
import copy


def comparison_response(baseline, names, player_id):
    result = copy.deepcopy(baseline.compare(player_id))
    result['reference']['name'] = names[player_id]
    for comparison in result['comparisons']:
        comparison['name'] = names[comparison['player_id']]
    result['season'] = '2024-25'
    result['exposure_policy'] = 'No extra games/minutes cutoff; compare exact games and cumulative season minutes for each checkpoint.'
    result['warnings'].append('Limited playing time can produce unstable rates or zero-distance matches without reliable player equivalence. Scaler filtering is not adopted; all eligible players still contribute.')
    return result
