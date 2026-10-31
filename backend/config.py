import os

DATABASE_URL = os.getenv('AGENTBAILOUT_DATABASE_URL', 'sqlite:///./agentbailout.db')
STAGE_SECONDS = max(0.0, float(os.getenv('AGENTBAILOUT_STAGE_SECONDS', '0.5')))
