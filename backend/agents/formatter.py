def run(data: dict) -> dict:
    if not data.get('findings'):
        raise ValueError('Research findings are required')
    return {'title': data['topic'], 'sections': [
        {'heading': f'Finding {i}', 'body': finding}
        for i, finding in enumerate(data['findings'], 1)], 'source': data['source']}
