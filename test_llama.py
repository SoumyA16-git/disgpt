import os
from dotenv import load_dotenv
import urllib.request
import urllib.error
import json
import time

load_dotenv()
api_key = os.environ.get('OPENROUTER_API_KEY')

req = urllib.request.Request(
    'https://openrouter.ai/api/v1/chat/completions',
    headers={
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    },
    data=json.dumps({
        'model': 'meta-llama/llama-3.3-70b-instruct:free',
        'messages': [{'role': 'user', 'content': 'Test ping'}]
    }).encode('utf-8')
)

start = time.time()
print('Sending request to Llama 70B Free...')
try:
    res = urllib.request.urlopen(req)
    print(f'Time: {time.time()-start:.2f}s')
    print(json.loads(res.read())['choices'][0]['message']['content'])
except urllib.error.HTTPError as e:
    print(f'HTTPError: {e.code} - {e.read().decode()}')
except Exception as e:
    print(f'Error: {str(e)}')
