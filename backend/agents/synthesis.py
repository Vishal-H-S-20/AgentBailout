def run(data: dict) -> dict:
    if not data.get('sections'):
        raise ValueError('Formatted sections are required')
    return {'title': data['title'], 'summary': '\n'.join(
        section['body'] for section in data['sections']),
        'recommendation': 'Start with a scoped pilot and measure outcomes before expanding.',
        'source': data['source']}
