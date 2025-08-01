import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Clear all proxy env vars to avoid conflicts
proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'all_proxy', 'socks_proxy', 'SOCKS_PROXY']
for proxy_var in proxy_vars:
    os.environ.pop(proxy_var, None)

url = os.environ["URL"]
key = os.environ["KEY"]

try:
    supabase: Client = create_client(url, key)
except Exception as e:
    print(f"Supabase connection error: {e}")
    supabase = None

def get_proxies(limit=50):
    if not supabase:
        return []
    try:
        response = supabase.table('proxies').select('*').limit(limit).execute()
        return [row['proxy_url'] for row in response.data]
    except Exception as e:
        print(f"Error fetching proxies: {e}")
        return []

def get_configs(limit=5):
    if not supabase:
        return []
    try:
        response = supabase.table('configs').select('*').limit(limit).execute()
        return [row['config_url'] for row in response.data]
    except Exception as e:
        print(f"Error fetching configs: {e}")
        return []