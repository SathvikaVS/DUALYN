STATUS_RANK = {'missing': 0, 'needs_improvement': 1, 'covered': 2}
CHANGE_ORDER = {'improved': 0, 'declined': 1, 'new': 2, 'removed': 3, 'unchanged': 4}


def compare_analyses(old, new):
    """
    Compares two SkillAnalysis snapshots skill by skill.
    Pure deterministic logic: no AI, no new database rows.
    """
    old_gaps = {g.skill_id: g for g in old.gaps.select_related('skill')}
    new_gaps = {g.skill_id: g for g in new.gaps.select_related('skill')}

    changes = []

    for skill_id, new_gap in new_gaps.items():
        old_gap = old_gaps.get(skill_id)
        if old_gap is None:
            change, old_status = 'new', None
        else:
            old_status = old_gap.status
            diff = STATUS_RANK[new_gap.status] - STATUS_RANK[old_gap.status]
            change = 'improved' if diff > 0 else 'declined' if diff < 0 else 'unchanged'
        changes.append({
            'skill': new_gap.skill,
            'old_status': old_status,
            'new_status': new_gap.status,
            'change': change,
        })

    for skill_id, old_gap in old_gaps.items():
        if skill_id not in new_gaps:
            changes.append({
                'skill': old_gap.skill,
                'old_status': old_gap.status,
                'new_status': None,
                'change': 'removed',
            })

    changes.sort(key=lambda c: (CHANGE_ORDER[c['change']], c['skill'].name))

    return {
        'score_change': round(new.readiness_score - old.readiness_score, 1),
        'changes': changes,
        'improved_count': sum(1 for c in changes if c['change'] == 'improved'),
        'declined_count': sum(1 for c in changes if c['change'] == 'declined'),
    }