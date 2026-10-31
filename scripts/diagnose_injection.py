"""Capture current duplicate-fault error details using the supported API."""
import httpx
with httpx.Client(base_url="http://127.0.0.1:8003",timeout=10) as client:
    response=client.post("/tasks",json={"prompt":"Inspect controlled fault persistence","failure":{"scenario":"crash","stage_index":1}})
    response.raise_for_status()
    identity=response.json()["id"]
    result=client.post(f"/tasks/{identity}/inject-failure",json={"scenario":"crash","stage_index":1})
    print("Task:",identity)
    print("Expected duplicate rejection:",result.status_code,result.text)
    assert result.status_code==409
    assert result.json()["detail"]["code"]=="FAULT_ALREADY_CONFIGURED"
