import re
import json

log_file_path = r"C:\Users\shahzaib.khan1\Downloads\SFS_2023_11_14-12_46_37_959_startup.log"

pattern = re.compile(r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{6})\s+(?P<log_level>\d+)\s+DEBUG:\s+\[\s+{tenant:(?P<tenant_id>\d+),\s+ixn:(?P<ixn_id>\d+)(?:,\s+agent:(?P<agent_id>\d+))?.*?\]\s+(?P<arrow><-|->)\s+im:\s+(?P<event>\w+)\s+\(header:(?P<header>[^~]+)\)\s.*?~~')

with open(log_file_path, 'r') as file:
    log_lines = file.read()

matches = re.finditer(pattern, log_lines)

for match in matches:
    timestamp = match.group('timestamp')
    tenant_id = match.group('tenant_id')
    ixn_id = match.group('ixn_id')
    agent_id = match.group('agent_id')
    log_level = match.group('log_level')
    arrow = match.group('arrow')
    event = match.group('event')
    header_str = match.group('header')

    print(f"Timestamp: {timestamp}, Tenant ID: {tenant_id}, Ixn ID: {ixn_id}, Agent ID: {agent_id}, Log Level: {log_level}, Arrow: {arrow}, Event: {event}")
    
    # Extract key-value pairs from the header string by splitting only the first colon
    header_pairs = [pair.strip().split(':', 1) for pair in header_str.split(',') if pair.strip()]
    header_obj = dict((key.strip(), value.strip()) for key, value in header_pairs)

    print(f"Header as Object: {json.dumps(header_obj, indent=2)}")
    print("=" * 50)
