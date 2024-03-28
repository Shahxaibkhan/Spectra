# se_page.py

from flask import Flask, render_template, request, send_file
import io
import os
import zipfile
import re
from datetime import datetime
import json
import tempfile
from .base_page import BasePage
from pages.ssh_handler import fetch_log_files

class SEPage(BasePage):

    def __init__(self, app):
        self.app = app


    def analyze(self):
        # Implement SE analysis logic here
        return render_template('se.html')


    def analyze_vectors(self):
        log_file = self.file_upload_and_processing_logs()
        sorted_logs = self.vectors_processed_logs(log_file)
        current_dir = os.getcwd()
        output_file = os.path.join(current_dir, "vector_details.log")

        # Convert logs to JSON
        logs_json = self.convert_logs_to_json(sorted_logs)

        # Save JSON to a file
        with open(output_file, 'w') as file:
            file.write(logs_json)

        return send_file(output_file, as_attachment=True, download_name="vector_details.json")


    def fetch_and_analyze_se_logs(self, selected_ips, logs_path, username, password):
        all_logs_content = []  # List to store log lines from all selected IPs

        # Iterate over selected IPs
        for host in selected_ips:
            try:
                log_files_content = self.fetch_se_logs(host, logs_path, username, password)

                if log_files_content:
                    all_logs_content.extend(log_files_content)
            except Exception as e:
                print(f"Failed to fetch logs from {host}: {e}")

        if all_logs_content:
            # Create a temporary file to store all logs
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8') as temp_file:
                try:
                    # Write all logs to the temporary file
                    temp_file.writelines(all_logs_content)

                    # Move the file cursor to the beginning for reading
                    temp_file.seek(0)

                    

                    # Read the content into a list
                    logfile = temp_file.readlines()

                    # Pass the list of log lines to the analysis method
                    return self.generate_se_stats(logfile)
                except Exception as e:
                    print(f"Error processing logs: {e}")
        else:
            print("No logs fetched from any machine.")
            return None

    

        

    def fetch_se_logs(self,host, logs_path, username, password):
        logs_path = logs_path.rstrip('/')  # Remove trailing slash if present
        logs_path = f"{logs_path}/script_executor/"  # Append "/script_executor/"
        
        logs = fetch_log_files(host, username, password, logs_path)

        if logs is not None:
            print("Logs Found:")
            print("-" * 50)
            return logs
        else:
            print("Failed to fetch logs. Check SSH connection.")
            return None

    def display_checks_stats(self):
        checks_stats = self.generate_checks()
        # Return the generated statistics to be displayed in the HTML template
        return render_template('checks_stats.html', checks_stats=checks_stats)

    def generate_stats(self):
        log_file = self.file_upload_and_processing_logs()
        return self.generate_se_stats(log_file)

    def generate_se_stats(self,log_file):
        # Generate summary report
        summary_report = self.generate_summary_report(log_file)
        # Return the generated summary report to be displayed in the HTML template
        return render_template('se_stats.html', summary_report=summary_report)
  
    def generate_ixn_stats(self,log_file,ixn,tenant):
        vector_stats = self.generate_vector_stats(log_file,ixn,tenant)

        # Extract unique vector_ids from vector_stats and count occurrences
        vector_id_counts = {}
        for entry in vector_stats:
            vector_id = entry.get('vector_id')
            if vector_id:
                vector_id_counts[vector_id] = vector_id_counts.get(vector_id, 0) + 1

        total_vectors = len(vector_id_counts)
        return vector_stats , total_vectors
    

    def generate_summary_report(self,log_file):
        vector_stats = self.generate_vector_stats(log_file)
        check_results = self.generate_checks(log_file)
        check_dn_details_json = self.dn_details(log_file)
        check_vector_details_json = self.vector_details(log_file)
        check_tenant_add_details = self.tenant_add_details(log_file)
        # Process results for summary report
        total_calls = len(vector_stats)

        print(check_tenant_add_details)
        # Parse the JSON string into a list of dictionaries
        check_dn_details = json.loads(check_dn_details_json)

        # Initialize variables for max and min processing times
        max_processing_times_dn = {'insert': float('-inf'), 'change': float('-inf')}
        min_processing_times_dn = {'insert': float('inf'), 'change': float('inf')}
        max_processing_time_dn_keys = {'insert': None, 'change': None}
        min_processing_time_dn_keys = {'insert': None, 'change': None}
        # Iterate through the entries
        for entry in check_dn_details:
            # Check if 'requests' key exists and is a list
            if isinstance(entry.get('requests'), list):
                for request in entry['requests']:
                    # Access 'processing_time' directly from 'request'
                    processing_time = request.get('processing_time')

                    if processing_time is not None:
                        request_type = request.get('request_type')

                        # Check for maximum processing time
                        if processing_time > max_processing_times_dn.get(request_type, float('-inf')):
                            max_processing_times_dn[request_type] = processing_time
                            max_processing_time_dn_keys[request_type] = request.get('key')

                        # Check for minimum processing time
                        if processing_time < min_processing_times_dn.get(request_type, float('inf')):
                            min_processing_times_dn[request_type] = processing_time
                            min_processing_time_dn_keys[request_type] = request.get('key')

        

        check_vector_details = json.loads(check_vector_details_json)

        max_processing_times_vec = {'insert': float('-inf'), 'change': float('-inf')}
        min_processing_times_vec = {'insert': float('inf'), 'change': float('inf')}
        max_processing_time_vec_keys = {'insert': None, 'change': None}
        min_processing_time_vec_keys = {'insert': None, 'change': None}
        # Iterate through the entries
        for entry in check_vector_details:
            # Check if 'requests' key exists and is a list
            if isinstance(entry.get('requests'), list):
                for request in entry['requests']:
                    # Access 'processing_time' directly from 'request'
                    processing_time = request.get('processing_time')

                    if processing_time is not None:
                        request_type = request.get('request_type')

                        # Check for maximum processing time
                        if processing_time > max_processing_times_vec.get(request_type, float('-inf')):
                            max_processing_times_vec[request_type] = processing_time
                            max_processing_time_vec_keys[request_type] = request.get('key')

                        # Check for minimum processing time
                        if processing_time < min_processing_times_vec.get(request_type, float('inf')):
                            min_processing_times_vec[request_type] = processing_time
                            min_processing_time_vec_keys[request_type] = request.get('key')


        # Extract unique vector_ids from vector_stats and count occurrences
        vector_id_counts = {}
        for entry in vector_stats:
            vector_id = entry.get('vector_id')
            if vector_id:
                vector_id_counts[vector_id] = vector_id_counts.get(vector_id, 0) + 1

        total_vectors = len(vector_id_counts)

        # Initialize max_processing_vector and min_processing_vector
        max_processing_vector = None
        min_processing_vector = None

                # Check if vector_stats is not empty before finding max and min
        if vector_stats:
            # Find the vector with maximum processing time
            max_processing_vector = max(vector_stats, key=lambda x: x.get('total_execution_time', 0))

            # Find the vector with minimum processing time
            min_processing_vector = min(vector_stats, key=lambda x: x.get('total_execution_time', 0))
        else:
            # Handle the case when vector_stats is empty
            max_processing_vector = {"vector_id": "N/A", "total_execution_time": "N/A"}
            min_processing_vector = {"vector_id": "N/A", "total_execution_time": "N/A"}

        # Extract vectors loaded and compilation time from check_results
        vectors_loaded = 0
        compilation_time = 0

        for check_result in check_results:
            if check_result["check_name"] == "Vector Loaded and Compilation Time":
                vectors_loaded = check_result["vectors_loaded"]
                compilation_time = check_result["compilation_time"]
                break

        # Count the number of DN added and edited
        dn_added_count = 0
        dn_edited_count = 0

        for dn_detail in check_dn_details:
            
            # Check if 'requests' key exists and is a list
            if 'requests' in dn_detail and isinstance(dn_detail['requests'], list):
                for request in dn_detail['requests']:
                    
                    request_type = request.get('request_type', '').lower()
                    
                    if request_type == 'insert':
                        dn_added_count += 1
                    elif request_type == 'change':
                        dn_edited_count += 1


        # Count the number of Vectors added and edited
        vector_added_count = 0
        vector_edited_count = 0

        for vector_detail in check_vector_details:
            
            # Check if 'requests' key exists and is a list
            if 'requests' in vector_detail and isinstance(vector_detail['requests'], list):
                for request in vector_detail['requests']:
                    
                    request_type = request.get('request_type', '').lower()
                    
                    if request_type == 'insert':
                        vector_added_count += 1
                    elif request_type == 'change':
                        vector_edited_count += 1
            else:
                print("Invalid or missing 'requests' key in vector_detail")

        summary_report = {
            "max_processing_vec": {
                "insert": {
                    "vec_id": max_processing_time_vec_keys['insert'] if max_processing_time_vec_keys['insert'] is not None else 'N/A',
                    "total_execution_time": max_processing_times_vec['insert'] if max_processing_time_vec_keys['insert'] is not None else 'N/A'
                },
                "change": {
                    "vec_id": max_processing_time_vec_keys['change'] if max_processing_time_vec_keys['change'] is not None else 'N/A',
                    "total_execution_time": max_processing_times_vec['change'] if max_processing_time_vec_keys['change'] is not None else 'N/A'
                }
            },
            "min_processing_vec": {
                "insert": {
                    "vec_id": min_processing_time_vec_keys['insert'] if min_processing_time_vec_keys['insert'] is not None else 'N/A',
                    "total_execution_time": min_processing_times_vec['insert'] if min_processing_time_vec_keys['insert'] is not None else 'N/A'
                },
                "change": {
                    "vec_id": min_processing_time_vec_keys['change'] if min_processing_time_vec_keys['change'] is not None else 'N/A',
                    "total_execution_time": min_processing_times_vec['change'] if min_processing_time_vec_keys['change'] is not None else 'N/A'
                }
            },
            "max_processing_dn": {
                "insert": {
                    "dn_id": max_processing_time_dn_keys['insert'] if max_processing_time_dn_keys['insert'] is not None else 'N/A',
                    "total_execution_time": max_processing_times_dn['insert'] if max_processing_time_dn_keys['insert'] is not None else 'N/A'
                },
                "change": {
                    "dn_id": max_processing_time_dn_keys['change'] if max_processing_time_dn_keys['change'] is not None else 'N/A',
                    "total_execution_time": max_processing_times_dn['change'] if max_processing_time_dn_keys['change'] is not None else 'N/A'
                }
            },
            "min_processing_dn": {
                "insert": {
                    "dn_id": min_processing_time_dn_keys['insert'] if min_processing_time_dn_keys['insert'] is not None else 'N/A',
                    "total_execution_time": min_processing_times_dn['insert'] if min_processing_time_dn_keys['insert'] is not None else 'N/A'
                },
                "change": {
                    "dn_id": min_processing_time_dn_keys['change'] if min_processing_time_dn_keys['change'] is not None else 'N/A',
                    "total_execution_time": min_processing_times_dn['change'] if min_processing_time_dn_keys['change'] is not None else 'N/A'
                }
            },
            
            "total_ixns": total_calls,
            "total_vectors": total_vectors,
            "max_processing_vector": {
                "vector_id": max_processing_vector.get('vector_id', 'N/A'),
                "total_execution_time": max_processing_vector.get('total_execution_time', 'N/A')
            },
            "min_processing_vector": {
                "vector_id": min_processing_vector.get('vector_id', 'N/A'),
                "total_execution_time": min_processing_vector.get('total_execution_time', 'N/A')
            },
            "vectors_loaded": vectors_loaded,
            "compilation_time": compilation_time,
            "vector_stats_details": vector_stats,
            "dn_details": check_dn_details,
            "vector_details": check_vector_details,
            "vector_id_counts": vector_id_counts,
            "dn_added_count": dn_added_count,
            "dn_edited_count": dn_edited_count,
            "vector_added_count": vector_added_count,
            "vector_edited_count": vector_edited_count,
            "tenant_add_details": check_tenant_add_details
        }

        return summary_report

    def tenant_add_details(self, logs):
        tenant_details = {}

        # Process logs sequentially
        for log in logs:
            # Extract tenant addition start information
            start_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[\d+\]  INFO : \[ ScriptExecutorConfigManager::subTenantAdd > NewTenantID:(\d+), NewTenantName:(\w+) \]~~', log)
            if start_match:
                log_timestamp = start_match.group(1)
                tenant_id = start_match.group(2)
                tenant_name = start_match.group(3)

                tenant_details[tenant_id] = {
                    "tenant_name": tenant_name,
                    "start_time": datetime.strptime(log_timestamp, '%Y-%m-%d %H:%M:%S,%f'),
                    "end_time": None,
                    "processing_time": None,
                }

            # Extract tenant addition completion information
            complete_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[\d+\]  INFO : \[ ScriptExecutorConfigManager::registerDynamicNotificationHandlers > Subscribers added for tenantName:(\w+), tenantID(\d+) \]~~', log)
            if complete_match:
                log_timestamp = complete_match.group(1)
                tenant_name = complete_match.group(2)
                tenant_id = complete_match.group(3)

                if tenant_id in tenant_details:
                    end_time = datetime.strptime(log_timestamp, '%Y-%m-%d %H:%M:%S,%f')
                    start_time = tenant_details[tenant_id]["start_time"]
                    processing_time = (end_time - start_time).total_seconds()* 1000

                    # Update tenant details with completion information
                    tenant_details[tenant_id]["end_time"] = end_time
                    tenant_details[tenant_id]["processing_time"] = processing_time
                    print("processing time:",processing_time)

        # Calculate the total number of tenants added
        total_tenants_added = len(tenant_details)

        return {
            "tenant_details": tenant_details,
            "total_tenants_added": total_tenants_added
        }


    def vector_details(self, logs):
        details_map = {}

        # Initialize key_map
        key_map = {}

        current_key_info = None

        # Process logs sequentially
        for log in logs:
            # Extract keys from the first set of logs
            match = re.search(r'\[ Received routing-entity-(\w+) event with id: re_(?:add|change)_(\w+)_vector tenant: (\w+) entity: vector key: (\d+) event time: (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+Z) \]~~', log)
            if match:
                key = match.group(4)
                request_type = match.group(1)
                tenant_name = match.group(3)
                entity_type = "vector"
                event_time = match.group(5)

                current_key_info = {
                    "request_type": request_type,
                    "tenant_name": tenant_name,
                    "entity": entity_type,
                    "key": key,
                    "event_time": datetime.strptime(event_time, '%Y-%m-%dT%H:%M:%S.%fZ'),
                }

                key_map.setdefault(key, {"request": None, "requests": []})
                key_map[key]["requests"].append(current_key_info)
                key_map[key]["request"] = current_key_info

            # Process payload logs
            payload_match = re.search(r'Payload:(.*?)]~~', log)
            if payload_match:
                payload_str = payload_match.group(1).strip()

                try:
                    payload_details = json.loads(payload_str)
                    key_from_payload = payload_details.get("key", -1)
                    entity_type_from_payload = payload_details.get("type")
                    if key_from_payload in key_map:
                        for request in key_map[key_from_payload]["requests"]:
                            if not request.get("payload_details") and entity_type_from_payload == request.get("entity"):
                                request["payload_details"] = payload_details
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")

            # Look for synchronization logs
            sync_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[\d+\]  DEBUG: \[ ScriptExecutor::compileVectorRE > Vector updated\. ID:(\d+)\|(\d+\.\d+\.\d+) \]', log)
            if sync_match:
                log_timestamp = sync_match.group(1)
                entity_key = sync_match.group(2)

                try:
                    entity_id = sync_match.group(3).split('.')[-1]
                    if entity_id in key_map:
                        for request in key_map[entity_id]["requests"]:
                            if not request.get("sync_details"):                   
                                sync_time = datetime.strptime(log_timestamp, '%Y-%m-%d %H:%M:%S,%f')
                                # Extract event_time from the request
                                event_time = request.get("event_time")

                                if event_time:
                                    # Convert both sync_time and event_time to timestamps (floats)
                                    sync_timestamp = sync_time.timestamp()
                                    event_timestamp = event_time.timestamp()

                                    # Calculate processing time
                                    processing_time_seconds = sync_timestamp - event_timestamp

                                    # Add processing time directly to the request
                                    request["processing_time"] = processing_time_seconds

                                # Add synchronization details to the correct key in key_map
                                sync_details = {
                                    "entity_key": entity_key,
                                    "entity_id": entity_id,
                                    "sync_time": sync_time,
                                }
                                key_map[entity_id]["request"]["sync_logs"] = sync_details
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")

        # Sort requests within each key based on timestamps
        for key in key_map:
            key_map[key]["requests"] = sorted(key_map[key]["requests"], key=lambda x: x["event_time"])

        # Convert key_map to a list before returning
        result_list = [{"requests": v["requests"]} for v in key_map.values()]


        # Convert the result to JSON-formatted string
        result_json = json.dumps(result_list, default=str)
        # print(f"final step: {result_json}")
        return result_json


    def dn_details(self, logs):
        details_map = {}

        # Initialize key_map
        key_map = {}

        current_key_info = None

        # Process logs sequentially
        for log in logs:
            # Extract keys from the first set of logs
            match = re.search(r'\[ Received routing-entity-(\w+) event with id: re_(?:add|change)_(\w+)_callType tenant: (\w+) entity: callType key: (\d+) event time: (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+Z) \]~~', log)
          
            if match:
                key = match.group(4)
                request_type = match.group(1)
                tenant_name = match.group(3)
                entity_type = "callType"
                event_time = match.group(5)

                current_key_info = {
                    "request_type": request_type,
                    "tenant_name": tenant_name,
                    "entity": entity_type,
                    "key": key,
                    "event_time": datetime.strptime(event_time, '%Y-%m-%dT%H:%M:%S.%fZ'),
                }

                key_map.setdefault(key, {"request": None, "requests": []})
                key_map[key]["requests"].append(current_key_info)
                key_map[key]["request"] = current_key_info
        

                # print("entry: ",key_map[key]["request"])

            # Process payload logs
            payload_matches = re.finditer(r'Payload:(.*?)]~~', log)
            for payload_match in payload_matches:
                payload_str = payload_match.group(1).strip()

                try:
                    payload_details = json.loads(payload_str)
                    key_from_payload = payload_details.get("key", -1)
                    entity_type_from_payload = payload_details.get("type")

                    if key_from_payload in key_map and entity_type_from_payload == key_map[key_from_payload]["request"]["entity"]:
                        key_map[key_from_payload]["request"]["payload_details"] = payload_details
                    # print("entry2: ",key_map[key]["request"])
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")

            # Look for synchronization logs
            sync_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}).*DN synchronized, DN:\d+\|(\d+\.\d+\.\d+), Entity:dn', log)

            if sync_match:
                log_timestamp = sync_match.group(1)
                sync_id = sync_match.group(2)

                sync_time = datetime.strptime(log_timestamp, '%Y-%m-%d %H:%M:%S,%f')
                entity_id = int(sync_id.split('.')[-1])
                for key in key_map:
                    try:
                        if key_map[key]["request"]["payload_details"]["data"]["id"] == entity_id:
                            for request in key_map[key]["requests"]:
                                if not request.get("sync_details"):
                                    log_timestamp = sync_match.group(1)
                                    sync_time = datetime.strptime(log_timestamp, '%Y-%m-%d %H:%M:%S,%f')

                                    # Extract event_time from the request
                                    event_time = request.get("event_time")

                                    if event_time:
                                        # Convert both sync_time and event_time to timestamps (floats)
                                        sync_timestamp = sync_time.timestamp()
                                        event_timestamp = event_time.timestamp()

                                        # Calculate processing time
                                        processing_time_seconds = sync_timestamp - event_timestamp

                                        # Add processing time directly to the request
                                        key_map[key]["request"]["processing_time"] = processing_time_seconds

                                    # Add synchronization details to the correct key in key_map
                                    sync_details = {
                                        "entity_id": entity_id,
                                        "sync_time": sync_time,
                                    }
                                    key_map[key]["request"]["sync_logs"] = sync_details

                                    # Break out of the loop to move to the next key
                                    break
                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON: {e}")

        # Sort requests within each key based on timestamps
        for key in key_map:
            key_map[key]["requests"] = sorted(key_map[key]["requests"], key=lambda x: x["event_time"])

        # Convert key_map to a list before returning
        result_list = [{"requests": v["requests"]} for v in key_map.values()]


        # # Convert key_map to a list before returning
        # result_list = [v for v in key_map.values()]

        # Convert the result to JSON-formatted string
        result_json = json.dumps(result_list, default=str)
        return result_json



    def generate_checks(self,logs):
        
        vector_stats = []

        for log in logs:
            # Use a single regular expression to capture both values in one go
            match = re.search(r'Vector compilation took:(\d+)\s*sec.*Number of Vectors loaded:(\d+)', log)
            
            if match:
                compilation_time = int(match.group(1))
                vectors_loaded = int(match.group(2))
                vector_stats.append({
                    "check_name": "Vector Loaded and Compilation Time",
                    "compilation_time": compilation_time,
                    "vectors_loaded": vectors_loaded,
                })

                

              
        return vector_stats


    def generate_vector_stats(self,log_file, ixn=None, tenant=None):
        # Get processed logs
        sorted_logs = self.vectors_processed_logs(log_file, ixn, tenant)

        vector_stats = []

        # Create a dictionary to store vector statistics
        vector_statistics = {}

        for log in sorted_logs:
            key = f"{log['tenant_id']}_{log['call_id']}_{log['vector_id']}"
            
            if key not in vector_statistics:
                vector_statistics[key] = {
                    'vector_id': log['vector_id'],
                    'call_id': log['call_id'],
                    'total_execution_time': 0,
                    'number_of_steps': 0,
                    'tenant_id': log['tenant_id'],
                    'contains_first_step': False,
                    'contains_last_step': False,
                }

            vector_statistics[key]['number_of_steps'] += 1
            vector_statistics[key]['total_execution_time'] += log['execution_time']
            vector_statistics[key]['contains_first_step'] = vector_statistics[key]['contains_first_step'] or log['first_step']
            vector_statistics[key]['contains_last_step'] = vector_statistics[key]['contains_last_step'] or log['is_last_step']

        # Convert dictionary to a list
        for key, stats in vector_statistics.items():
            vector_stats.append(stats)

        return vector_stats


    def convert_logs_to_json(self, sorted_logs):
        # Create a dictionary to store logs based on call_id and vector_id
        logs_by_call_vector = {}

        for log in sorted_logs:
            call_id = log['call_id']
            vector_id = log['vector_id']
            timestamp = log['timestamp']
            execution_index = log['execution_index']
            tenant_id = log['tenant_id']
            execution_time = log['execution_time']

            # Create a unique identifier for the log entry
            log_identifier = f"{vector_id}_{call_id}_{timestamp}_{execution_index}_{tenant_id}"

            # Convert the tuple key to a string
            key_str = f"{call_id}_{vector_id}"

            # Check if the (call_id, vector_id) pair is already in the dictionary
            if key_str not in logs_by_call_vector:
                logs_by_call_vector[key_str] = {
                    'call_id': call_id,
                    'vector_id': vector_id,
                    'tenant_id': tenant_id,
                    'total_execution_steps': 0,
                    'total_execution_time': 0,
                    'logs': []
                }

            # Increment the total execution steps for the (call_id, vector_id) pair
            logs_by_call_vector[key_str]['total_execution_steps'] += 1

            # Add the log details to the dictionary entry
            logs_by_call_vector[key_str]['total_execution_time'] += execution_time
            logs_by_call_vector[key_str]['logs'].append({
                'log_identifier': log_identifier,
                'timestamp': timestamp,
                'execution_index': execution_index,
                'is_last_step': log['is_last_step'],
                'first_step': log['first_step'],
                'log_line': log['matched_string'],
                'execution_time': execution_time
            })

        # # Convert the dictionary to a JSON object
        # logs_json = json.dumps(logs_by_call_vector, indent=2)
        
        # output_file_path = "se_output.json"
        # with open(output_file_path, 'w') as output_file:
        #     output_file.write(logs_json)

        return logs_json


    def vectors_processed_logs(self,log_file, ixn=None, tenant=None):
            

            parsed_vector_logs = [result for log in log_file if (result := self.parse_vector_log(log, ixn, tenant)) is not None]

            # Check if any logs were parsed
            if not parsed_vector_logs:
                # Handle the case when no logs were parsed
                return []

            sorted_logs = sorted(parsed_vector_logs, key=lambda x: (x['call_id'],x['vector_id'],x['tenant_id'], x['timestamp'], x['execution_index']))

            # logs_json = json.dumps(sorted_logs, indent=2)
            
            # output_file_path = "se_output.json"
            # with open(output_file_path, 'w') as output_file:
            #  output_file.write(logs_json)


            
            return sorted_logs



    def file_upload_and_processing_logs(self):
            log_file = request.files['se_file']

            # Get the current working directory
            current_dir = os.getcwd()

            # Specify the directory for saving and reading files
            upload_dir = os.path.join(current_dir, 'se_logs_files')
            
            # Ensure the directory exists
            os.makedirs(upload_dir, exist_ok=True)

            # Save uploaded files with absolute paths
            log_file_path = os.path.join(upload_dir, 'se.log')
            log_file.save(log_file_path)

            with open(log_file_path, 'r') as log_file:
                log_file =log_file.readlines()

            return log_file

            # parsed_log_file = [self.parse_im_log(log) for log in log_file if self.parse_im_log(log) is not None]

            # # Check if any logs were parsed
            # if not parsed_log_file:
            #     # Handle the case when no logs were parsed
            #     return []

            # sorted_logs = sorted(parsed_log_file, key=lambda x: (x['ixnid'], x['event_name'], x['agent_id'] if x['agent_id'] is not None else 0, x['tenant_id'], x['timestamp']))

            # return sorted_logs



    def parse_vector_log(self,log, ixn=None, tenant=None):
            search_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[\d+\]  DEBUG: \[ VectorScript::executeVectorSteps: > Time taken for script execution:(\d+) usecs\. CallID:(\d+\|\d+\.\d+\.\d+), VecID:(\d+\|\d+\.\d+\.\d+), isLastStep:(true|false), executionIndex:(\d+) \]~~'
            log_pattern = re.compile(search_pattern)
            logpattern_match = log_pattern.search(log)

            if logpattern_match:
                result = {}  # Object to store the extracted values
                call_id_tenant_str = logpattern_match.group(3)
                result["tenant_id"], result["call_id"] = map(int, call_id_tenant_str.split('|')[1].split('.')[0:3:2])
                
                if ixn is None or (result["call_id"] == int(ixn) and result["tenant_id"] == int(tenant) ):
                

                    result["matched_string"] = logpattern_match.group()
                    result["timestamp"] = logpattern_match.group(1)
                    result["execution_time"] = int(logpattern_match.group(2))

                    call_id_tenant_str = logpattern_match.group(3)
                    result["call_id_tenant_str"] = call_id_tenant_str
                    result["tenant_id"], result["call_id"] = map(int, call_id_tenant_str.split('|')[1].split('.')[0:3:2])

                    vector_id_tenant_str = logpattern_match.group(4)
                    result["vector_id_tenant_str"] = vector_id_tenant_str
                    result["vector_id"] = int(vector_id_tenant_str.split('|')[1].split('.')[2])

                    result["is_last_step"] = logpattern_match.group(5).lower() == "true"
                    result["execution_index"] = int(logpattern_match.group(6))

                    # Include a key "first_step" set to True if execution index is 0, else False
                    result["first_step"] = result["execution_index"] == 0


                    return result

            # If no match is found, return None'
            return None




    