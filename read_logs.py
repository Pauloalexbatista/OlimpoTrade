import json
with open(r'C:\Users\paulo\.gemini\antigravity\brain\bba089c1-d93e-45f3-8888-d58f7b6d9504\.system_generated\logs\transcript.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        content = data.get('content', '')
        if 'navegar' in content.lower() or '<' in content or '>' in content:
            if 'USER_INPUT' in data.get('type', ''):
                print(f"USER: {content[:200]}")
