import json

log_file = r"C:\Users\user\.gemini\antigravity\brain\05c996e4-020c-4b88-8d54-5f1da297bbff\.system_generated\logs\transcript.jsonl"

print("Searching for commands run in the past...")
with open(log_file, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            # Find tool calls of type command execution
            if 'tool_calls' in data:
                for tc in data['tool_calls']:
                    if 'CommandLine' in tc.get('arguments', {}):
                        cmd = tc['arguments']['CommandLine']
                        print(f"Step {data.get('step_index', '?')}: {cmd}")
            # Find user requests
            if data.get('type') == 'USER_INPUT' and 'content' in data:
                print(f"User Input step {data.get('step_index', '?')}: {data['content'][:200]}")
        except Exception as e:
            pass
