import re

def extract_tenant_ixn_from_log(log):
    pattern = r'tenant_id:(\d+).*?ixn_id:(\d+).*?session_id:(\d+)'
    match = re.search(pattern, log)

    if match:
        result = {
            "tenant_id": int(match.group(1)),
            "ixn_id": int(match.group(2)),
            "session_id": int(match.group(3))
        }
        return result
    return None

def parse_trace_log(log, session_id_details):
    pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{6})\s+(\d+)\s+TRACE: \[ {session_id:(\d+)} \[SFS\.ctxwkr\] (.+?) \]~~'
    match = re.search(pattern, log)

    if match:
        result = {
            "timestamp": match.group(1),
            "thread_id": int(match.group(2)),
            "session_id": int(match.group(3)),
            "log_type": "TRACE",
            "event_details": match.group(4)
        }

        if result["session_id"] in session_id_details:
            result.update(session_id_details[result["session_id"]])

        return result

    return None

# Specify the path to your log file and output file
input_file_path = 'D:\\pythonUtility\\sfsreq\\SFS_2023_12_18-12_35_06_642.log'
output_file_path = 'D:\\pythonUtility\\sfsreq\\output.txt'

# Dictionary to store extracted tenant, ixn, and session ids
session_id_details = {}

# Read log lines from the file and extract tenant, ixn, and session ids
with open(input_file_path, 'r') as file:
    for log_line in file:
        details = extract_tenant_ixn_from_log(log_line)
        if details:
            # Store unique records based on session_id
            if details["session_id"] not in session_id_details:
                session_id_details[details["session_id"]] = {"tenant_id": details["tenant_id"],"ixn_id": details["ixn_id"]}
                print (session_id_details[details["session_id"]])

# Write the results to the output file
with open(output_file_path, 'w') as output_file:
    # Read log lines again and apply the parsing function
    with open(input_file_path, 'r') as file:
        for log_line in file:
            result = parse_trace_log(log_line, session_id_details)
            if result:
                output_file.write(str(result) + '\n')
