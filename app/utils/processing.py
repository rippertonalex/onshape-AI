import json

def simplify_data(raw_data):
    def flatten_geometry(entity):
        geom = entity.get('geometry', {}).get('message', {})
        geom_type = entity.get('geometry', {}).get('typeName', '').lower()
        simplified = {
            'type': None,
            'entityId': entity.get('entityId')
        }

        if 'line' in geom_type:
            simplified['type'] = 'line'
            simplified.update({
                'pntX': geom.get('pntX'),
                'pntY': geom.get('pntY'),
                'dirX': geom.get('dirX'),
                'dirY': geom.get('dirY')
            })
        elif 'circle' in geom_type:
            simplified['type'] = 'circle'
            simplified.update({
                'xCenter': geom.get('xCenter'),
                'yCenter': geom.get('yCenter'),
                'radius': geom.get('radius')
            })
        elif 'arc' in geom_type:
            simplified['type'] = 'arc'
            simplified.update({
                'centerX': geom.get('xCenter'),
                'centerY': geom.get('yCenter'),
                'radius': geom.get('radius'),
                'startAngle': geom.get('startParam'),
                'sweep': geom.get('endParam')  # sometimes only parametric range is given
            })
        elif 'point' in entity.get('typeName', '').lower():
            simplified['type'] = 'point'
            simplified.update({
                'x': entity.get('message', {}).get('x'),
                'y': entity.get('message', {}).get('y')
            })
        else:
            return None  # Ignore unknown types

        return simplified

    # Extract sketch entities
    features = raw_data.get('features', [])
    sketch_entities = []
    constraints = []

    for feature in features:
        if feature.get('featureType') == 'newSketch':
            for entity in feature.get('entities', []):
                simplified = flatten_geometry(entity)
                if simplified:
                    sketch_entities.append(simplified)

            for constraint in feature.get('constraints', []):
                constraints.append({
                    'type': constraint.get('constraintType'),
                    'entities': constraint.get('entityList', []),
                    'parameters': {
                        p['parameterId']: p.get('value') or p.get('expression')
                        for p in constraint.get('parameters', [])
                    }
                })

    return {
        'geometry': sketch_entities,
        'constraints': constraints
    }

# Usage
with open("output (2).json") as f:
    raw = json.load(f)

cleaned = simplify_sketch_data(raw)

with open("cleaned_sketch.json", "w") as f:
    json.dump(cleaned, f, indent=2)
