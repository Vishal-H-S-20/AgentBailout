import re


def run(data: dict) -> dict:
    topic = data['prompt'].strip()
    keywords = list(dict.fromkeys(re.findall(r'[a-zA-Z]{3,}', topic.lower())))[:8]
    return {'topic': topic, 'keywords': keywords,
            'findings': [f'Define the scope and success criteria for: {topic}',
                         f'Evaluate dependencies and risks related to {", ".join(keywords) or "the topic"}.',
                         'Compare alternatives with a small, measurable pilot.'],
            'source': 'Deterministic planning simulation; no external research performed.'}
