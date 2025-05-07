FILTER_CONFIG = {
    'feature_3d': {
        'exclude_fields': ['type'],
        'conditional_exclude': [],
    },
    'extrude': {
        'exclude_fields': [],
        'conditional_exclude': []
    },
    'fillet': {
        'exclude_fields': [],
        'conditional_exclude': [
            {
                'fields': ['startPartialType', 'startPartialOffset', 'endPartialType', 'endPartialOffset', 'partialFirstEdgeTotalParameter', 'partialOppositeParameter', 'startPartialEntity', 'endPartialEntity'], 
                'condition_field': 'isPartial',
                'condition_value': False
            }
        ]
    },
    'feature_2d': {
        'exclude_fields': [],
        'conditional_exclude': []
    },
    'entity': {
        'exclude_fields': [],
        'conditional_exclude': []
    },
    'constraint': {
        'exclude_fields': ['typeName', 'helpParameters', 'index', 'hasUserCode', 'nodeId'],
        'conditional_exclude': [
            {
                'field': 'pierceParameter',
                'condition_field': 'hasPierceParameter',
                'condition_value': False
            },
            {
                'fields': ['offsetOrientation1', 'offsetDistance1'],
                'condition_field': 'hasOffsetData1',
                'condition_value': False
            },
            {
                'fields': ['offsetOrientation2', 'offsetDistance2'],
                'condition_field': 'hasOffsetData2',
                'condition_value': False
            }
        ]
    },
    'constraint_parameter': {
        'exclude_fields': ['typeName', 'helpParameters', 'index', 'hasUserCode', 'nodeId'],
        'conditional_exclude': []
    }, # TODO implement this filter properly
    'parameter': {
        'exclude_fields': [],
        'conditional_exclude': []
    }
}

def apply_filters(data, config):
    # If data is a list of dicts (e.g., parameters), filter by parameterId or similar key
    if isinstance(data, list):
        key_name = config.get('match_key', 'parameterId')
        exclude_fields = set(config.get('exclude_fields', []))
        filtered = []
        # First, handle conditional_exclude rules that depend on the value of a specific parameter
        for rule in config.get('conditional_exclude', []):
            # Find the dict with parameterId == condition_field
            condition_dict = next((item for item in data if isinstance(item, dict) and item.get(key_name) == rule['condition_field']), None)
            if condition_dict and condition_dict.get('value') == rule['condition_value']:
                # Remove all dicts whose parameterId is in rule['fields'] or is the condition_field itself
                fields_to_remove = set(rule.get('fields', [])) | {rule['condition_field']}
                data = [item for item in data if not (isinstance(item, dict) and item.get(key_name) in fields_to_remove)]
        # Now handle exclude_fields as usual
        for item in data:
            if isinstance(item, dict) and key_name in item and item[key_name] in exclude_fields:
                continue
            filtered.append(item)
        return filtered
    # Otherwise, treat as dict
    for field in config.get('exclude_fields', []):
        data.pop(field, None)
    for rule in config.get('conditional_exclude', []):
        if (
            rule['condition_field'] in data and
            data.get(rule['condition_field']) == rule['condition_value']
        ):
            data.pop(rule['condition_field'], None)
            if 'fields' in rule:
                for f in rule['fields']:
                    data.pop(f, None)
            elif 'field' in rule:
                data.pop(rule['field'], None)
    return data