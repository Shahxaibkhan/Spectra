import re

def extract_execution_info(log_file_path, search_pattern):
    # Define the regex pattern for specific log lines
    log_pattern = re.compile(search_pattern)

    # Lists to store matched timestamps, execution times, CallID, and TenantID
    matched_timestamps = []
    matched_execution_times = []
    matched_call_ids = []
    matched_tenant_ids = []
    matched_vector_id = []

    with open(log_file_path, 'r') as file:
        for line in file:
            match = log_pattern.search(line)
            if match:
                timestamp = match.group(1)  # Extract the timestamp from the regex match
                execution_time = int(match.group(2))  # Extract the execution time and convert to integer
                call_id_tenant_str = match.group(3)  # Extract the CallID and TenantID string
                vector_id_tenant_str = match.group(4)  # Extract the CallID and TenantID string
                is_last_step = match.group(5)  # Extract the isLastStep value
                execution_index = int(match.group(6))  # Extract the execution index and convert to integer

                # Extract CallID and TenantID from the CallID and TenantID string
                tenant_id, call_id = map(int, call_id_tenant_str.split('|')[1].split('.')[0:3:2])
                vec_id = int(vector_id_tenant_str.split('|')[1].split('.')[2])


                matched_timestamps.append(timestamp)
                matched_execution_times.append(execution_time)
                matched_call_ids.append(call_id)
                matched_tenant_ids.append(tenant_id)
                matched_vector_id.append(vec_id)

    return matched_timestamps, matched_execution_times, matched_call_ids, matched_tenant_ids, matched_vector_id

# Example usage
log_file_path = 'log_2023_12_13-08_03_07_startup.log'
search_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[\d+\]  DEBUG: \[ VectorScript::executeVectorSteps: > Time taken for script execution:(\d+)usecs\. CallID:(\d+\|\d+\.\d+\.\d+), VecID:(\d+\|\d+\.\d+\.\d+), isLastStep:(true|false), executionIndex:(\d+) \]~~'
timestamps, execution_times, call_ids, tenant_ids, Vector_id = extract_execution_info(log_file_path, search_pattern)

# Display the matched information
for timestamp, execution_time, call_id, tenant_id, Vector_id in zip(timestamps, execution_times, call_ids, tenant_ids, Vector_id):
    print(f"Timestamp: {timestamp}, Execution Time: {execution_time} usecs, CallID: {call_id}, TenantID: {tenant_id}, VectorId: {Vector_id}")
