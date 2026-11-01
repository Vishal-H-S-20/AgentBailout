"""Explicit data contracts shared by providers and recovery candidates."""
from jsonschema import Draft202012Validator
from backend.agents import research, formatter, synthesis


def obj(properties: dict) -> dict:
    return {'type':'object', 'properties':properties, 'required':list(properties), 'additionalProperties':False}


TEXT = {'type':'string', 'minLength':1}
PROMPT = obj({'prompt':TEXT})
RESEARCH = obj({'topic':TEXT,'keywords':{'type':'array','items':TEXT},
                'findings':{'type':'array','items':TEXT,'minItems':1},'source':TEXT})
REPORT = obj({'title':TEXT,'sections':{'type':'array','items':obj({'heading':TEXT,'body':TEXT}),'minItems':1},'source':TEXT})
SUMMARY = obj({'title':TEXT,'summary':TEXT,'recommendation':TEXT,'source':TEXT})
DOCUMENT = obj({'topic':TEXT,'content':TEXT,'source':TEXT})
CONTRACTS = {
    'research':(PROMPT,RESEARCH), 'format':(RESEARCH,REPORT), 'summarize':(REPORT,SUMMARY),
    'plan':(PROMPT,DOCUMENT), 'code':(DOCUMENT,DOCUMENT), 'validate':(DOCUMENT,DOCUMENT),
    'extract':(PROMPT,DOCUMENT), 'transform':(DOCUMENT,DOCUMENT), 'review':(DOCUMENT,DOCUMENT)}
CONTRACTS['custom']=({'type':'object'},{'type':'object','properties':{'content':{}},'required':['content']})
TEMPLATES = {
    'research': [('Research','research'),('Formatter','format'),('Synthesis','summarize')],
    'coding': [('Plan','plan'),('Generate Code','code'),('Validate','validate')],
    'document': [('Extract Information','extract'),('Transform','transform'),('Review','review')]}

CONTRACT_NAMES = [(PROMPT,'Task brief'),(RESEARCH,'Research findings'),(REPORT,'Formatted report'),
                  (SUMMARY,'Final summary'),(DOCUMENT,'Working document')]
OPERATION_NAMES={'custom':'Custom LLM stage','research':'Research','format':'Format','summarize':'Summarize','plan':'Plan','code':'Generate Code','validate':'Validate','extract':'Extract','transform':'Transform','review':'Review'}


def contract_name(schema: dict) -> str:
    return next((name for expected,name in CONTRACT_NAMES if expected==schema),'Custom data')


def compatible_operations(schema: dict) -> list[str]:
    return [operation for operation,(required,_) in CONTRACTS.items() if required==schema]


def catalog() -> dict:
    return {operation:{'label':OPERATION_NAMES[operation],'input':contract_name(required),'output':contract_name(produced),
                       'input_schema':required,'output_schema':produced,'next':compatible_operations(produced)}
            for operation,(required,produced) in CONTRACTS.items() if operation!='custom'}


def validate(data: dict, schema: dict) -> None:
    Draft202012Validator(schema).validate(data)


def offline(operation: str, data: dict) -> dict:
    if operation in {'research','format','summarize'}:
        return {'research':research.run,'format':formatter.run,'summarize':synthesis.run}[operation](data)
    topic = data.get('prompt', data.get('topic',''))
    previous = data.get('content', topic)
    actions = {
        'plan':f'Plan for {topic}: define inputs, implement a pure function, review with examples.',
        'code':f'# Offline illustrative code for: {topic}\ndef normalize_text(value: str) -> str:\n    return " ".join(value.split())\n',
        'validate':f'Static review only; code was not executed. Check that behavior matches the requested task.\n{previous}',
        'extract':f'Explicit words: {", ".join(topic.split())}',
        'transform':previous.upper(),
        'review':f'Reviewed deterministic transformation; verify domain accuracy before use.\n{previous}'}
    return {'topic':topic,'content':actions[operation],
            'source':'Offline deterministic simulation; no external LLM, tool or generated code executed.'}
