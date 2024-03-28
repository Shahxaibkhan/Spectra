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

class SFSPage(BasePage):

    def __init__(self, app):
        self.app = app


    def analyze(self):
        # Implement IM analysis logic here
        return render_template('sfs.html')


    def analyze_wrkr_threads(self):
        print('i am here')
        log_file = self.file_upload_and_processing_logs()
        sorted_logs = self.wrkr_processed_logs(log_file)
        current_dir = os.getcwd()
        output_file = os.path.join(current_dir, "wrkrthreads_details.log")

        # Convert logs to JSON
        logs_json = self.convert_logs_to_json(sorted_logs)

        # Save JSON to a file
        with open(output_file, 'w') as file:
            file.write(logs_json)

        return send_file(output_file, as_attachment=True, download_name="worker_threads.json")

    
    def display_checks_stats(self):
        checks_stats = self.generate_checks()

        # Return the generated statistics to be displayed in the HTML template
        return render_template('checks_stats.html', checks_stats=checks_stats)


    def fetch_and_analyze_sfs_logs(self, selected_ips, logs_path, username, password):
        all_logs_content = []  # List to store log lines from all selected IPs

        # Iterate over selected IPs
        for host in selected_ips:
            try:
                log_files_content = self.fetch_sfs_logs(host, logs_path, username, password)

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
                    return self.generate_sfs_stats(logfile)
                except Exception as e:
                    print(f"Error processing logs: {e}")
        else:
            print("No logs fetched from any machine.")
            return None

    def fetch_sfs_logs(self,host, logs_path, username, password):
        logs_path = logs_path.rstrip('/')  # Remove trailing slash if present
        logs_path = f"{logs_path}/SFS/"  # Append "/script_executor/"
        
        logs = fetch_log_files(host, username, password, logs_path)

        if logs is not None:
            print("Logs Found")
            print("-" * 50)
            return logs
        else:
            print("Failed to fetch logs. Check SSH connection.")
            return None

    # def generate_sfs_ixn_stats(self,log_file):
    #     return self.generate_ixn_stats(log_file)
    
    def generate_ixn_stats(self,log_file,ixn,tenant):
        sorted_logs = self.call_processed_logs(log_file,ixn,tenant)
        # Convert logs to JSON
        logs_json = self.convert_sfsim_logs_to_json(sorted_logs)

        summary_data = self.generate_summary_report(logs_json)
        detailed_summary = self.generate_detailed_report(logs_json)

        return summary_data , detailed_summary
    
    
    def generate_stats(self):
        log_file = self.file_upload_and_processing_logs()
        return self.generate_sfs_stats(log_file)

    def generate_sfs_stats(self,log_file):
        # Generate summary report
        sorted_logs = self.call_processed_logs(log_file)
        # Convert logs to JSON
        logs_json = self.convert_sfsim_logs_to_json(sorted_logs)

        summary_data = self.generate_summary_report(logs_json)
        detailed_summary = self.generate_detailed_report(logs_json)

        # Return the generated summary report and detailed summary to be displayed in the HTML template
        return render_template('sfs_stats.html', summary_data=summary_data, detailed_summary=detailed_summary)


    def extract_sfsim_details(self):
        log_file = self.file_upload_and_processing_logs()
        sorted_logs = self.call_processed_logs(log_file)
        current_dir = os.getcwd()
        output_file = os.path.join(current_dir, "sfsim_details.log")

        # Convert logs to JSON
        logs_json = self.convert_sfsim_logs_to_json(sorted_logs)

        # Save JSON to a file
        with open(output_file, 'w') as file:
            file.write(logs_json)

        return send_file(output_file, as_attachment=True, download_name="sfsim.json")


    def generate_detailed_report(self, logs_json):
        # Parse the JSON data
        json_data = json.loads(logs_json)
        # Initialize detailed report data
        # Initialize the detailed_report list
        detailed_report = []

        # Iterate over each tenant in the JSON data
        for tenant_id, tenant_data in json_data.items():

            # Iterate over each ixn in the tenant_data
            for ixn_id, ixn_details in tenant_data.items():
                agent_ids = ixn_details.get('agent_ids', [])
                no_of_agents = len(agent_ids)

                # Check for duplicated events
                duplicate_events = ixn_details.get('duplicated_events', [])
                duplicate_events_count = len(duplicate_events)

                notify_dropout = any(event.get('event_name') == 'NotifyDropout' for event in ixn_details.get('events', []))
                transfer_scenario = ixn_details.get('TransferScenerio', False)
                conference_scenarios = [event for event in ixn_details.get('events', []) if event.get('event_name') == 'Merge']

                # Initialize transfer_details and conference_details as empty dictionaries
                transfer_details = {}
                conference_details = {}

                so_supervisors = set()
                for event in ixn_details.get('events', []):
                    supervisor_id = event.get('header', {}).get('supervisor_id', '')
                    if supervisor_id and supervisor_id != '0':
                        so_supervisors.add(supervisor_id)

                if transfer_scenario:
                    transfer_event = next((event for event in ixn_details.get('events', []) if event.get('event_name') == 'Transfer'), None)
                    if transfer_event:
                        transfer_details['destination_ixn_id'] = transfer_event.get('header', {}).get('destination_ixn_id', '')
                        transfer_details['transferror'] = transfer_event.get('header', {}).get('transferror', '')

                if conference_scenarios:
                    merge_event = conference_scenarios[0]  # Assuming there's only one Merge event in the list
                    conference_details['source_ixn_id'] = merge_event.get('header', {}).get('source_ixn_id', '')
                    conference_details['excepted_party'] = merge_event.get('header', {}).get('excepted_party', '')

                # Create a dictionary with the extracted information
                detailed_item = {
                    'ixn_id': ixn_id,
                    'tenant_id': tenant_id,
                    'no_of_agents': no_of_agents,
                    'duplicate_events': duplicate_events_count,
                    'notify_dropout': notify_dropout,
                    'transfer_details': transfer_details if transfer_scenario else '',
                    'conference_details': conference_details if conference_scenarios else ''
                }

                if so_supervisors:
                    detailed_item['so_supervisors'] = ', '.join(so_supervisors)

                # Append the dictionary to the detailed_report list
                detailed_report.append(detailed_item)


        return detailed_report





    def generate_summary_report(self,logs_json):

        # Parse the JSON data
        json_data = json.loads(logs_json)

        # Call the sfs_im_events_processing function to get imEvents_data
        result_data = self.sfs_im_events_processing(json_data)
        
        # Parse the details_json string into a dictionary
        imEvents_data = json.loads(result_data['details_json'])


        # Initialize summary data
        summary_data = {
            'total_ixns': 0,
            'transfer_scenarios': 0,
            'conference_cases': 0,
            'so_cases': 0,
            'duplicated_events_ixns': 0,
            'notify_dropout_ixns': 0,
            'so_encountered_ixns': set(), 
            'imEvents_data': imEvents_data,
            'agent_ids': result_data['agent_ids_dict'],
            'trunk_ids': result_data['trunk_ids_dict'],
            'supervisor_ids': result_data['supervisor_ids_dict'],
            'max_processing_times': result_data['max_processing_times'],
            'min_processing_times': result_data['min_processing_times'],
            'events_without_receiving': result_data['events_without_receiving']
        }


        for tenant_id, tenant_data in json_data.items():
        # Process each ixn in the JSON data
            for ixn_id, ixn_details in tenant_data.items():
                summary_data['total_ixns'] += 1

                # Check for TransferScenerio
                if 'TransferScenerio' in ixn_details and ixn_details['TransferScenerio']:
                    summary_data['transfer_scenarios'] += 1

                # Check for conference cases (Merge event)
                events = ixn_details.get('events', [])  # Ensure 'events' is a list
                for event in events:
                    event_name = event.get('event_name', '')
                    if event_name == 'Merge':
                        summary_data['conference_cases'] += 1

                    # Check for SO cases (supervisor_id other than zero)
                    header = event.get('header', {})
                    supervisor_id = header.get('supervisor_id', '')
                    if supervisor_id and supervisor_id != '0' and ixn_id not in summary_data['so_encountered_ixns']:
                        summary_data['so_cases'] += 1
                        summary_data['so_encountered_ixns'].add(ixn_id)


                # Check for duplicated events
                if 'duplicated' in ixn_details and ixn_details['duplicated']:
                    summary_data['duplicated_events_ixns'] += 1

                # Check for NotifyDropout events
                events_with_notify_dropout = [event for event in events if event.get('event_name') == 'NotifyDropout']
                if events_with_notify_dropout:
                    summary_data['notify_dropout_ixns'] += 1

            
            

        return summary_data



    def sfs_im_events_processing(self, logs_data):
        # Dictionary to store paired events
        paired_events = {}

        # Dictionaries to store max and min processing times for each sending event
        max_processing_times = {}
        min_processing_times = {}

        # Counter for events without receiving events
        events_without_receiving = 0

        # Dictionary to store agent IDs
        agent_ids_dict = {}
        trunk_ids_dict = {}
        supervisor_ids_dict = {}

         # Iterate through tenant ids
        for tenant_id, tenant_data in logs_data.items():

            # Initialize agent_ids_dict for the current tenant
            agent_ids_dict.setdefault(tenant_id, {})

            # Initialize trunk_ids_dict for the current tenant
            trunk_ids_dict.setdefault(tenant_id, {})

            # Initialize supervisor_ids_dict for the current tenant
            supervisor_ids_dict.setdefault(tenant_id, {})

            # Iterate through logs
            for ixn_id, ixn_data in tenant_data.items():
                events = ixn_data.get('events', [])
                agent_ids = ixn_data.get('agent_ids')
                supervisor_ids = ixn_data.get('supervisor_ids')
                trunk_extensions = ixn_data.get('trunk_extensions')
               

                # Store agent_ids for the current tenant and ixn_id if available
                if agent_ids is not None:
                    agent_ids_dict[tenant_id].setdefault(ixn_id, []).extend(agent_ids)

                # Store trunk_extensions for the current tenant and ixn_id if available
                if trunk_extensions is not None:
                    trunk_ids_dict[tenant_id].setdefault(ixn_id, []).extend(trunk_extensions)

                # Store supervisor_ids for the current tenant and ixn_id if available
                if supervisor_ids is not None:
                    supervisor_ids_dict[tenant_id].setdefault(ixn_id, []).extend(supervisor_ids)


                ixn_events = []  # List to store events for each ixn_id
                
                # Iterate through sending events
                for sending_event in events:
                    
                    if sending_event['status'] == 'sending':
                        sent_event = sending_event['event_name']
                        sending_agent_id = sending_event['agent_id']
                        sending_agent_id_header = sending_event.get('header', {}).get('party', 'default_value')

                        
                        # Find corresponding receiving event
                        corresponding_receiving_event = self.get_corresponding_receiving_event(sent_event)
                        if corresponding_receiving_event is not None:
                            # Check if the corresponding receiving event is missing and timestamp order is correct
                            receiving_event_found = False
                            for receiving_event in events:
                                
                                if (
                                    receiving_event['status'] == 'receiving'
                                    and receiving_event['event_name'] == corresponding_receiving_event
                                    and (receiving_event['agent_id'] == sending_agent_id or receiving_event['header']['party'] == sending_agent_id_header)
                                    and datetime.strptime(receiving_event['timestamp'], "%Y-%m-%d %H:%M:%S,%f") > datetime.strptime(sending_event['timestamp'], "%Y-%m-%d %H:%M:%S,%f")
                                ):

                                    # Calculate time difference
                                    sending_time = datetime.strptime(sending_event['timestamp'], "%Y-%m-%d %H:%M:%S,%f")
                                    receiving_time = datetime.strptime(receiving_event['timestamp'], "%Y-%m-%d %H:%M:%S,%f")
                                    processing_time = (receiving_time - sending_time).total_seconds() * 1000

                                    # Collect details
                                    details = {
                                        'sending_event': sending_event,
                                        'receiving_event': receiving_event,
                                        'processing_time': processing_time,
                                    }

                                    ixn_events.append(details)  # Append details to the list
                                    receiving_event_found = True

                                    # Collect max and min processing times
                                    time_difference_seconds = processing_time

                                    if sent_event not in max_processing_times or time_difference_seconds > max_processing_times[sent_event]['time']:
                                        max_processing_times[sent_event] = {'time': time_difference_seconds, 'tenant_id': tenant_id, 'ixn_ids': ixn_id}
                                    elif time_difference_seconds == max_processing_times[sent_event]['time']:
                                        max_processing_times[sent_event]['tenant_id'] = tenant_id
                                        max_processing_times[sent_event]['ixn_ids'] = ixn_id

                                    if sent_event not in min_processing_times or time_difference_seconds < min_processing_times[sent_event]['time']:
                                        min_processing_times[sent_event] = {'time': time_difference_seconds, 'tenant_id': tenant_id, 'ixn_ids': ixn_id}
                                    elif time_difference_seconds == min_processing_times[sent_event]['time']:
                                        min_processing_times[sent_event]['tenant_id'] = tenant_id
                                        min_processing_times[sent_event]['ixn_ids'] = ixn_id


                                    break  # Break out of the loop once a matching receiving event is found

                            if not receiving_event_found:
                                # Corresponding receiving event is missing or timestamp order is incorrect
                                details = {
                                    'sending_event': sending_event,
                                    'receiving_event': None,
                                    'processing_time': 99999999,
                                }
                                ixn_events.append(details)  # Append details to the list

                                # Increment the counter for events without receiving events
                                events_without_receiving += 1

                paired_events.setdefault(tenant_id, {}).setdefault(ixn_id, []).extend(ixn_events)

        # Convert the dictionaries to lists for returning
        max_processing_times_list = [{'event_name': event, **details} for event, details in max_processing_times.items()]
        min_processing_times_list = [{'event_name': event, **details} for event, details in min_processing_times.items()]

        # Convert the dictionary to a JSON object
        details_json = json.dumps(paired_events, indent=2)

    #    # Write the JSON data to a file
        # output_file_path = "custom_output.json"
        # with open(output_file_path, 'w') as output_file:
        #     json.dump(paired_events, output_file, indent=2)

        # # Print max and min processing times for each sending event
        # print("Max processing times:")
        # for event_data in max_processing_times_list:
        #     print(f"  {event_data['event_name']}: {event_data['time']} (IXN IDs: {event_data['ixn_ids']})")

        # print("Min processing times:")
        # for event_data in min_processing_times_list:
        #     print(f"  {event_data['event_name']}: {event_data['time']} (IXN IDs: {event_data['ixn_ids']})")
            
        # # Print the count of events without receiving events
        # print(f"Number of events without receiving events: {events_without_receiving}")

        result_dict = {
            'details_json': details_json,
            'max_processing_times': max_processing_times,
            'min_processing_times': min_processing_times,
            'events_without_receiving': events_without_receiving,
            'agent_ids_dict': agent_ids_dict,
            'trunk_ids_dict': trunk_ids_dict,
            'supervisor_ids_dict': supervisor_ids_dict
        }
        return result_dict
    
    def get_corresponding_receiving_event(self,sending_event):
        # Define your mapping of sending events to corresponding receiving events here
        # This function should return the receiving event based on the sending event
        # For example:
        if sending_event in ['Route', 'RouteToSkill', 'Reroute']:
            return 'Routed'
        elif sending_event == 'Provision':
            return 'Provisioned'
        elif sending_event == 'Assign':
            return 'Assigned'
        elif sending_event == 'Connect':
            return 'Connected'
        elif sending_event == 'Hold':
            return 'Held'
        elif sending_event == 'Resume':
            return 'Resumed'
        elif sending_event == 'Transfer':
            return 'Transferred'
        elif sending_event == 'Merge':
            return 'Merged'
        elif sending_event == 'Dispose':
            return 'Disposed'
        elif sending_event == 'Terminate':
            return 'Terminated'
        elif sending_event == 'IgnoreAudit':
            return 'IgnoreAudit'
        elif sending_event == 'Audit_ixn':
            return 'Audited_ixn'
        elif sending_event == 'Audit_channel':
            return 'Audited_channel'
        # Add more cases as needed
        else:
            return None  # If no corresponding receiving event found


    def convert_logs_to_json(self,sorted_logs):
        logs_by_ixn_session_thread = {}

        for log in sorted_logs:
            ixn_id = log.get('ixn_id')
            session_id = log.get('session_id')
            thread_id = log.get('thread_id')
            timestamp = log.get('timestamp')
            log_type = log.get('log_type')
            event_details = log.get('event_details')

            # Create a unique identifier for the log entry
            log_identifier = f"{ixn_id}_{session_id}_{thread_id}_{timestamp}"

            # Check if the ixn_id is already in the dictionary
            if ixn_id not in logs_by_ixn_session_thread:
                logs_by_ixn_session_thread[ixn_id] = {'ixn_id':ixn_id}

            # Check if the session_id is already in the ixn_id dictionary
            if session_id not in logs_by_ixn_session_thread[ixn_id]:
                logs_by_ixn_session_thread[ixn_id][session_id] = {'session_id':session_id}

            # Check if the thread_id is already in the session_id dictionary
            if thread_id not in logs_by_ixn_session_thread[ixn_id][session_id]:
                logs_by_ixn_session_thread[ixn_id][session_id][thread_id] = {
                    'thread_id':thread_id,
                    'logs': []
                }

            # Add the log details to the dictionary entry
            logs_by_ixn_session_thread[ixn_id][session_id][thread_id]['logs'].append({
                'log_identifier': log_identifier,
                'timestamp': timestamp,
                'log_type': log_type,
                'event_details': event_details
            })

        # Convert the dictionary to a JSON object
        logs_json = json.dumps(logs_by_ixn_session_thread, indent=2)

        return logs_json
    
    def convert_sfsim_logs_to_json(self, sorted_logs):
        json_data = {}

        for log in sorted_logs:
            ixn_id = log['ixn_id']
            tenant_id = log['tenant_id']
            event_name = log['event']
            timestamp = log['timestamp']
            agent_id = log['agent_id']
            trunk_extension = log['trunk_extension']
            supervisor_id = log['supervisor_id']
            status = log['status']
            header = log['header']

            # Create or update entries in the JSON data
            json_data.setdefault(tenant_id, {})
            json_data[tenant_id].setdefault(ixn_id, {'supervisor_ids': [], 'trunk_extensions': [], 'agent_ids': [], 'events': [], 'duplicated_events': []})
            
            if agent_id is not None and agent_id not in json_data[tenant_id][ixn_id]['agent_ids']:
                json_data[tenant_id][ixn_id]['agent_ids'].append(agent_id)
            if trunk_extension is not None and trunk_extension not in json_data[tenant_id][ixn_id]['trunk_extensions']:
                json_data[tenant_id][ixn_id]['trunk_extensions'].append(trunk_extension)
            if supervisor_id is not None and supervisor_id not in json_data[tenant_id][ixn_id]['supervisor_ids']:
                json_data[tenant_id][ixn_id]['supervisor_ids'].append(supervisor_id)

            # Check if the event is already present (excluding timestamp)
            duplicate_event = next(
                (event for event in json_data[tenant_id][ixn_id]['events'] if event['event_name'] == event_name
                and event['header'] == header and event['status'] == status and event['agent_id'] == agent_id),
                None
            )

            if duplicate_event:
                # Mark as duplicated
                json_data[tenant_id][ixn_id]['duplicated'] = True

                # Create a copy of the original event and add details to the duplicated_events list
                original_event_copy = {
                    'event_name': duplicate_event['event_name'],
                    'timestamp': duplicate_event['timestamp'],
                    'status': duplicate_event['status'],
                    'agent_id': duplicate_event['agent_id'],
                    'header': duplicate_event['header']
                }

                json_data[tenant_id][ixn_id]['duplicated_events'].append(original_event_copy)
            else:
                # Add new event details
                json_data[tenant_id][ixn_id]['events'].append({
                    'event_name': event_name,
                    'timestamp': timestamp,
                    'status': status,
                    'agent_id': agent_id,
                    'header': header
                })

            # Check if the event is "Transfer" and extract additional details
            if event_name == "Transfer":
                transfer_details = {
                    'TransferScenerio': True,
                    'destination_ixn_id': header.get('destination_ixn_id', ''),
                    'transferror': header.get('transferror', '')
                }
                json_data[tenant_id][ixn_id].update(transfer_details)

        output_file_path='debug_output.json'
        # # Write JSON data to output file for debugging
        with open(output_file_path, 'w') as output_file:
            json.dump(json_data, output_file, indent=2)

        # Convert the JSON data to a JSON-formatted string
        json_string = json.dumps(json_data, indent=2)

        return json_string


    def call_processed_logs(self, log_file, ixn=None, tenant=None):
        parsed_log_file = [result for log in log_file if (result := self.parse_sfsim_logs(log, ixn, tenant)) is not None]
        
        if not parsed_log_file:
            # Handle the case when no logs were parsed
            return []

        sorted_logs = sorted(parsed_log_file, key=lambda x: (x['ixn_id'], x['tenant_id'], x['timestamp'],x['event'], x['agent_id'],x['trunk_extension'],x['supervisor_id']))

        return sorted_logs



    def wrkr_processed_logs(self,log_file):
            session_id_details = {}
            for log_line in log_file:
                details = self.extract_tenant_ixn_from_log(log_line)
                if details:
                    # Store unique records based on session_id
                    if details["session_id"] not in session_id_details:
                        session_id_details[details["session_id"]] = {"tenant_id": details["tenant_id"],"ixn_id": details["ixn_id"]}
                        
            
            
            parsed_vector_logs = [result for log in log_file if (result := self.parse_trace_log(log, session_id_details)) is not None]

            # Check if any logs were parsed
            if not parsed_vector_logs:
                # Handle the case when no logs were parsed
                return []

            
            sorted_logs = sorted(parsed_vector_logs, key=lambda x: (
                x.get('ixn_id', 0),        # Replace 0 with a default value if needed
                x.get('session_id', 0),    # Replace 0 with a default value if needed
                x.get('thread_id', 0),     # Replace 0 with a default value if needed
                x.get('tenant_id', 0),     # Replace 0 with a default value if needed
                x.get('timestamp', 0)      # Replace 0 with a default value if needed
            ))

            return sorted_logs



    def file_upload_and_processing_logs(self):
            log_file = request.files['sfs_file']

            # Get the current working directory
            current_dir = os.getcwd()

            # Specify the directory for saving and reading files
            upload_dir = os.path.join(current_dir, 'sfs_logs_files')
            
            # Ensure the directory exists
            os.makedirs(upload_dir, exist_ok=True)

            # Save uploaded files with absolute paths
            log_file_path = os.path.join(upload_dir, 'sfs.log')
            log_file.save(log_file_path)

            with open(log_file_path, 'r') as log_file:
                log_file =log_file.readlines()

            return log_file

           

  

    def parse_sfsim_logs(self, log, ixn=None, tenant=None):
        result = {}

        pattern = re.compile(r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{6})\s+(?P<log_level>\d+)\s+DEBUG:\s+\[\s+{tenant:(?P<tenant_id>\d+),\s+ixn:(?P<ixn_id>\d+)(?:,\s+(?P<agent_type>agent|extrunk|supervisor): *(?P<agent_value>\d+))?.*?\]\s+(?P<arrow><-|->)\s+im:\s+(?P<event>\w+)\s+\(header:(?P<header>[^~]+)\)\s.*?~~')

        match = re.search(pattern, log)

        # pattern = re.compile(r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{6})\s+(?P<log_level>\d+)\s+DEBUG:\s+\[\s+{tenant:(?P<tenant_id>\d+),\s+ixn:(?P<ixn_id>\d+)(?:,\s+(?P<agent_type>agent|extrunk|supervisor): *(?P<agent_value>\d+))?.*?\]\s+(?P<arrow><-|->)\s+im:\s+(?P<event>\w+)\s+\(header:(?P<header>[^~]+)\)\s.*?~~')
        # # pattern = re.compile(r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{6})\s+(?P<log_level>\d+)\s+DEBUG:\s+\[\s+{tenant:(?P<tenant_id>\d+),\s+ixn:(?P<ixn_id>\d+),\s+(?P<agent_type>agent|extrunk|supervisor): *(?P<agent_value>\d+)(?:,\s+.*?)*?\]\s+(?P<arrow><-|->)\s+im:\s+(?P<event>\w+)\s+\(header:(?P<header>[^~]+)\)\s.*?~~')

        # match = re.search(pattern, log)

        if match:
            ixn_id = match.group('ixn_id')
            tenant_id = match.group('tenant_id')

            # Check if ixn parameter is provided and ixn_id matches it
            if ixn is None or (ixn_id == str(ixn) and tenant_id == str(tenant)):
                timestamp = match.group('timestamp')
                ixn_id = ixn if ixn else match.group('ixn_id')
                agent_type = match.group('agent_type')
                agent_value = match.group('agent_value')
                log_level = match.group('log_level')
                status = 'sending' if match.group('arrow') == '->' else 'receiving'
                event = match.group('event')
                header_str = match.group('header')

                if agent_type == 'agent':
                    agent_id = agent_value
                    trunk_extension = None
                    supervisor_id = None
                elif agent_type == 'extrunk':
                    trunk_extension = agent_value
                    agent_id = None
                    supervisor_id = None
                elif agent_type == 'supervisor':
                    supervisor_id = agent_value
                    agent_id = None
                    trunk_extension = None
                else:
                    supervisor_id = None
                    agent_id = None
                    trunk_extension = None

                # Extract key-value pairs from the header string by splitting only the first colon
                header_pairs = [pair.strip().split(':', 1) for pair in header_str.split(',') if pair.strip()]
                header_obj = dict((key.strip(), value.strip()) for key, value in header_pairs)

                result['timestamp'] = timestamp
                result['tenant_id'] = tenant_id
                result['supervisor_id'] = supervisor_id
                result['trunk_extension'] = trunk_extension
                result['ixn_id'] = ixn_id
                result['agent_id'] = agent_id
                result['log_level'] = log_level
                result['status'] = status
                result['event'] = event
                result['header'] = header_obj

                # print(f"Timestamp: {timestamp}, Tenant ID: {tenant_id}, Ixn ID: {ixn_id}, Agent ID: {agent_id}, Log Level: {log_level}, Event: {event}, Header: {header_obj}")
                # # print(f"Header as Object: {json.dumps(header_obj, indent=2)}")
                # print("=" * 50)

                return result

        return None