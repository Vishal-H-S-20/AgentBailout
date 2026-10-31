from decimal import Decimal


def rank_candidates(candidates: list[dict], strategy: str) -> list[dict]:
    """Deterministic expected cost/time estimates, never claims measured forecasts."""
    metrics=[]
    for agent in candidates:
        probability=max(Decimal('.001'),Decimal(agent['selection_reliability']))
        cost=(Decimal(agent['estimated_cost'])+Decimal('.05'))/probability
        duration=Decimal(str(agent['estimated_latency']))/probability
        metrics.append((agent,cost,duration,probability))
    max_cost=max((m[1] for m in metrics),default=Decimal(1)) or Decimal(1)
    max_time=max((m[2] for m in metrics),default=Decimal(1)) or Decimal(1)
    def score(item):
        agent,cost,duration,probability=item
        value=cost if strategy=='cost' else duration if strategy=='time' else Decimal('.4')*cost/max_cost+Decimal('.35')*duration/max_time+Decimal('.25')*(1-probability)
        return value,-probability,agent['id'],agent['version']
    return [item[0] for item in sorted(metrics,key=score)]
