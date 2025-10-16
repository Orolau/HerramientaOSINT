import requests

def make_get_request(onSucces, onError, url):
    r = requests.get(url)
    if r.status_code == 200:
       onSucces(r.content)
    else:
        onError(r.status_code)

def make_POST_request(onSucces, onError, url, payload, headers):
    r = requests.post(url, json=payload, headers=headers)
    if r.status_code == 200:
       onSucces(r.content)
    else:
        onError(r.status_code)