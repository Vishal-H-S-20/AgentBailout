import os
import httpx
import streamlit as st

BASE=os.getenv('AGENTBAILOUT_BACKEND_URL','http://127.0.0.1:8003')


@st.cache_resource
def client():
    return httpx.Client(base_url=BASE,timeout=30)


def api(method: str,path: str,**kwargs):
    response=client().request(method,path,**kwargs)
    response.raise_for_status()
    return response.json()
