# im_page.py

import io, os, zipfile, re
import json, tempfile
from datetime import datetime
from .base_page import BasePage
from pages.ssh_handler import fetch_log_files
from flask import Flask, render_template, request, send_file



class IMPage(BasePage):

    def __init__(self, app):
        self.app = app


    def analyze(self):
        # Implement IM analysis logic here
        return render_template('im.html')

    # def generate_stats(self):
        
    #     return self.generate_im_stats(log_file)

    # def generate_im_stats(self,log_file):
    #     # Generate summary report
    #     summary_report = self.generate_summary_report(log_file)
    #     # Return the generated summary report to be displayed in the HTML template
    #     return render_template('im_stats.html', summary_report=summary_report)py sp   

    def upload_im(self):
        log_file = self.file_upload_and_processing_logs()
        sorted_im_ams_logs = self.fetch_im_ams_sorted_logs(log_file)
        current_dir = os.getcwd()
        # Specify the output file for the analysis with an absolute path
        output_file = os.path.join(current_dir, "IM_ams_flow.log")
        with open(output_file, 'w') as file:
            return self.write_IM_sorted_logs(file, sorted_im_ams_logs, [])

    
    def generate_stats(self):
        log_file = self.file_upload_and_processing_logs()
        return self.generate_im_stats(log_file)

    def fetch_and_analyze_im_logs(self, selected_ips, logs_path, username, password):
        all_logs_content = []  # List to store log lines from all selected IPs

        # Iterate over selected IPs
        for host in selected_ips:
            try:
                log_files_content = self.fetch_im_logs(host, logs_path, username, password)

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
                    return self.generate_im_stats(logfile)
                except Exception as e:
                    print(f"Error processing logs: {e}")
        else:
            print("No logs fetched from any machine.")
            return None

    def fetch_im_logs(self,host, logs_path, username, password):
        logs_path = logs_path.rstrip('/')  # Remove trailing slash if present
        logs_path = f"{logs_path}/interaction-manager-service/"  # Append "/script_executor/"
        
        logs = fetch_log_files(host, username, password, logs_path)

        if logs is not None:
            return logs
        else:
            print("Failed to fetch logs. Check SSH connection.")
            return None

    def generate_ixn_stats(self,log_file,ixn):
        return self.generate_summary_report(log_file,ixn)

    def generate_im_stats(self,log_file):
        # Generate summary report
        summary_data = self.generate_summary_report(log_file)
        # Return the generated summary report and detailed summary to be displayed in the HTML template
        return render_template(
            'im_stats.html',
            im_ams_event_details=summary_data['im_ams_event_details'],
            im_ams_processing_details=summary_data['im_ams_processing_details'],
            im_sfs_summary_data=summary_data['im_sfs_summary_data']
        )

    def generate_summary_report(self,logs, ixn=None):
        im_ams_jsonLogs = self.fetch_im_ams_json_logs(logs,ixn)
        im_ams_event_details = self.fetch_im_ams_event_details(im_ams_jsonLogs)
        im_ams_processing_details = self.fetch_im_ams_processing_details(im_ams_event_details['paired_events'])

        im_sfs_jsonLogs = self.fetch_im_sfs_json_logs(logs,ixn)
    

        # Call the sfs_im_events_processing function to get imEvents_data
        result_data = self.fetch_im_sfs_event_and_processing_details(im_sfs_jsonLogs)

        im_sfs_summary_data = {
            'agent_ids': result_data['agent_ids_dict'],
            'trunk_ids': result_data['trunk_ids_dict'],
            'supervisor_ids': result_data['supervisor_ids_dict'],
            'total_ixns': result_data['total_ixns'],
            'duplicated_events_ixns': result_data['duplicated_events_count'],
            'sfsEvents_data': result_data['paired_events'],
            'max_processing_times': result_data['max_processing_times'],
            'min_processing_times': result_data['min_processing_times'],
            'events_without_receiving': result_data['events_without_sending'],
        }
        
        

        summary_data = {
        "im_sfs_summary_data": im_sfs_summary_data,
        'im_ams_event_details': im_ams_event_details,
        'im_ams_processing_details': im_ams_processing_details
        }

        return summary_data


    def fetch_im_sfs_event_and_processing_details(self, im_sfs_json_logs):

        im_sfs_jsonLogs = json.loads(im_sfs_json_logs)
        
        # Dictionary to store paired events
        paired_events = {}

        # Dictionaries to store max and min processing times for each receiving event
        max_processing_times = {}
        min_processing_times = {}

        # Counter for events without sending events
        events_without_sending = 0

        duplicated_events_count = 0

        total_ixns = 0

        # Dictionary to store agent IDs
        agent_ids_dict = {}
        trunk_ids_dict = {}
        supervisor_ids_dict = {}

        # Iterate through tenant ids
        for tenant_id, tenant_data in im_sfs_jsonLogs.items():

            # Initialize agent_ids_dict for the current tenant
            agent_ids_dict.setdefault(tenant_id, {})

            # Initialize trunk_ids_dict for the current tenant
            trunk_ids_dict.setdefault(tenant_id, {})

            # Initialize supervisor_ids_dict for the current tenant
            supervisor_ids_dict.setdefault(tenant_id, {})
            
            # Iterate through ixn ids for each tenant
            for ixn_id, ixn_data in tenant_data.items():
                total_ixns += 1
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

                ixn_events =[]  # List to store events for each ixn_id
                 # Check for duplicated events
                if 'duplicated' in ixn_data and ixn_data['duplicated']:
                    duplicated_events_count += 1
                # Iterate through receiving events
                for receiving_event in events:
                    if receiving_event['status'] == 'receiving':
                        received_event = receiving_event['event_name']
                        receiving_agent_id = receiving_event['agent_id']

                        # Find corresponding sending event
                        corresponding_sending_event = self.get_corresponding_sending_event(received_event)
                
                        if corresponding_sending_event is not None:
                            # Check if the corresponding sending event is missing and timestamp order is correct
                            sending_event_found = False
    
                            for sending_event in events:
                                if (
                                        sending_event['status'] == 'sending'
                                        and sending_event['event_name'] == corresponding_sending_event
                                        and datetime.strptime(receiving_event['timestamp'], "%Y-%m-%d %H:%M:%S,%f") < datetime.strptime(sending_event['timestamp'], "%Y-%m-%d %H:%M:%S,%f")
                                        and (
                                            (sending_event['agent_id'] == receiving_agent_id and corresponding_sending_event != 'Merged')  # For events other than "Merged"
                                            or (
                                                corresponding_sending_event == 'Merged'  # For "Merge" event
                                                and (
                                                    sending_event['agent_id'] == receiving_agent_id
                                                    or sending_event['header']['source_ixn_id'] == receiving_event['header']['source_ixn_id']
                                                )
                                            )
                                            or (
                                                corresponding_sending_event == 'Transferred'  # For "Transferred" event
                                                and (
                                                    sending_event['agent_id'] == receiving_agent_id
                                                    or sending_event['header']['destination_ixn_id'] == receiving_event['header']['destination_ixn_id']
                                                )
                                            )
                                        )
                                    ):
                                    # Calculate time difference
                                    sending_time = datetime.strptime(sending_event['timestamp'], "%Y-%m-%d %H:%M:%S,%f")
                                    receiving_time = datetime.strptime(receiving_event['timestamp'], "%Y-%m-%d %H:%M:%S,%f")
                                    processing_time = (sending_time - receiving_time ).total_seconds() * 1000
                                    

                                    # Collect details
                                    details = {
                                        'sending_event': sending_event,
                                        'receiving_event': receiving_event,
                                        'processing_time': str(processing_time),
                                    }
                                    ixn_events.append(details)  # Append details to the list  # Append details to the list
                                    sending_event_found = True

                                    # Collect max and min processing times
                                    time_difference_seconds = processing_time

                                    if received_event not in max_processing_times or time_difference_seconds > max_processing_times[received_event]['time']:
                                        max_processing_times[received_event] = {'time': time_difference_seconds, 'tenant_id': tenant_id, 'ixn_id': ixn_id}
                                    elif time_difference_seconds == max_processing_times[received_event]['time']:
                                        max_processing_times[received_event]['tenant_id'] = tenant_id
                                        max_processing_times[received_event]['ixn_id'] = ixn_id

                                    if received_event not in min_processing_times or time_difference_seconds < min_processing_times[received_event]['time']:
                                        min_processing_times[received_event] = {'time': time_difference_seconds, 'tenant_id': tenant_id, 'ixn_id': ixn_id}
                                    elif time_difference_seconds == min_processing_times[received_event]['time']:
                                        min_processing_times[received_event]['tenant_id'] = tenant_id
                                        min_processing_times[received_event]['ixn_id'] = ixn_id

                                    break  # Break out of the loop once a matching sending event is found

                            if not sending_event_found:
                                # Corresponding sending event is missing or timestamp order is incorrect
                                details = {
                                    'receiving_event': receiving_event,
                                    'sending_event': None,
                                    'processing_time': "Missing or Incorrect Sending Event",
                                }
                                ixn_events.append(details)  # Append details to the list # Append details to the list
                                
                                # Increment the counter for events without sending events
                                events_without_sending += 1

                paired_events.setdefault(tenant_id, {}).setdefault(ixn_id, []).extend(ixn_events)

        # # Convert the dictionaries to lists for returning
        # max_processing_times_list = [{'event_name': event, **details} for event, details in max_processing_times.items()]
        # min_processing_times_list = [{'event_name': event, **details} for event, details in min_processing_times.items()]


        # Output agent IDs separately
        # agent_ids_json = json.dumps(agent_ids_dict, indent=2)
        # agent_ids_output_file_path = 'agentids_output.json'
        # with open(agent_ids_output_file_path, 'w') as agent_ids_output_file:
        #     json.dump(agent_ids_dict, agent_ids_output_file, indent=2)
        # # Convert the dictionary to a JSON object
        # details_json = json.dumps(paired_events, indent=2)

        # output_file_path='eventdetails_output.json'
        # # Write JSON data to output file for debugging
        # with open(output_file_path, 'w') as output_file:
            # json.dump(paired_events, output_file, indent=2)
        # Return the processed data
        # Create a dictionary to store the result
        result_dict = {
            'paired_events': paired_events,
            'max_processing_times': max_processing_times,
            'min_processing_times': min_processing_times,
            'events_without_sending': events_without_sending,
            'duplicated_events_count': duplicated_events_count,
            'total_ixns': total_ixns,
            'agent_ids_dict': agent_ids_dict,
            'trunk_ids_dict': trunk_ids_dict,
            'supervisor_ids_dict': supervisor_ids_dict
        }

        # Return the dictionary
        return result_dict


    def get_corresponding_sending_event(self,receiving_event):
        # Define your mapping of sending events to corresponding receiving events here
        # This function should return the receiving event based on the sending event
        # For example:
        if receiving_event in ['Route', 'RouteToSkill', 'Reroute']:
            return 'Routed'
        elif receiving_event == 'Provision':
            return 'Provisioned'
        elif receiving_event == 'Assign':
            return 'Assigned'
        elif receiving_event == 'Connect':
            return 'Connected'
        elif receiving_event == 'Hold':
            return 'Held'
        elif receiving_event == 'Resume':
            return 'Resumed'
        elif receiving_event == 'Transfer':
            return 'Transferred'
        elif receiving_event == 'Merge':
            return 'Merged'
        elif receiving_event == 'Dispose':
            return 'Disposed'
        elif receiving_event == 'Terminate':
            return 'Terminated'
        elif receiving_event == 'IgnoreAudit':
            return 'IgnoredAudit'
        elif receiving_event == 'Audit_ixn':
            return 'Audited_ixn'
        elif receiving_event == 'Audit_channel':
            return 'Audited_channel'
        # Add more cases as needed
        else:
            return None  # If no corresponding receiving event found


    def fetch_im_ams_json_logs(self,log_file, ixn=None):
        sorted_im_ams_logs = self.fetch_im_ams_sorted_logs(log_file, ixn)
        return self.convert_im_ams_logs_to_json(sorted_im_ams_logs)

    def fetch_im_sfs_json_logs(self,log_file, ixn=None):
        sorted_im_sfs_logs = self.fetch_im_sfs_sorted_logs(log_file,ixn)
        return self.convert_im_sfs_logs_to_json(sorted_im_sfs_logs)

    def convert_im_sfs_logs_to_json(self, sorted_logs):
        json_data = {}

        for log in sorted_logs:
            ixn_id = log['ixnid']
            tenant_id = log['tenant_id']
            event_name = log['event_name']
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

        # output_file_path='debug_output.json'
        # # # Write JSON data to output file for debugging
        # with open(output_file_path, 'w') as output_file:
        #     json.dump(json_data, output_file, indent=2)

        # Convert the JSON data to a JSON-formatted string
        json_string = json.dumps(json_data, indent=2)

        return json_string

    def fetch_im_ams_event_details(self, logs_json):
        paired_events = {}
        unique_event_pairs = set()
        event_occurrences = {}
        event_processing_times = {}

        for tenant_id, tenant_data in logs_json.items():
            paired_events[tenant_id] = {}
            for ixn_id, ixn_data in tenant_data.items():
                events = ixn_data['events']
                paired_events[tenant_id][ixn_id] = self.pair_events(events)

                for event in events:
                    event_name, event_data = list(event.items())[0]

                     # Count occurrences for sending events
                    if event_data['status'] == 'sending':
                        event_occurrences.setdefault(event_name, 0)
                        event_occurrences[event_name] += 1
                    

                    # Check if the event has a pairing
                    if 'sending_event' in event_data and 'receiving_event' in event_data:
                        # Create a unique identifier for the event pair
                        unique_pair_identifier = (
                            event_data['sending_event']['tenant_id'],
                            event_data['sending_event']['ixn_id'],
                            event_name
                        )

                        # Check if this pair has not been counted before
                        if unique_pair_identifier not in unique_event_pairs:
                            unique_event_pairs.add(unique_pair_identifier)

                            # Calculate processing times
                            if event_name in event_processing_times:
                                event_processing_times[event_name].append({
                                    'processing_time': self.calculate_processing_time(
                                        event_data['sending_event']['timestamp'],
                                        event_data['receiving_event']['timestamp']
                                    ),
                                    'tenant_id': tenant_id,
                                    'ixn_id': ixn_id
                                })
                            else:
                                event_processing_times[event_name] = [{
                                    'processing_time': self.calculate_processing_time(
                                        event_data['sending_event']['timestamp'],
                                        event_data['receiving_event']['timestamp']
                                    ),
                                    'tenant_id': tenant_id,
                                    'ixn_id': ixn_id
                                }]

        # Combine all information
        result_data = {
            'paired_events': paired_events,
            'event_occurrences': event_occurrences,
        }

        jsonLogs = json.dumps(result_data, indent=2)
        output_file_path = "ams_output.json"
        with open(output_file_path, 'w') as output_file:
            output_file.write(jsonLogs)
        return result_data


    def pair_events(self, events):
        paired_events = []
        sending_event = None


        for event in events:
            event_name, event_data = list(event.items())[0]

            if event_data['status'] == 'sending':
                sending_event = event_data
            elif event_data['status'] == 'receiving' and sending_event:
                receiving_event = event_data

                # Add conditions for pairing
                if (
                    sending_event['header']['tenant_id'] == receiving_event['header']['tenant_id']
                    and sending_event['header']['ixn_id'] == receiving_event['header']['ixn_id']
                    and sending_event['header']['request_time'] == receiving_event['header']['request_time']
                ):
                    processing_time = self.calculate_processing_time(
                        sending_event['timestamp'], receiving_event['timestamp']
                    )

                    paired_event = {
                        'sending_event': sending_event,
                        'receiving_event': receiving_event,
                        'processing_time': processing_time,
                    }

                    paired_events.append({event_name: paired_event})
                    sending_event = None

        return paired_events



    
    def calculate_processing_time(self, sending_timestamp, receiving_timestamp):

        # Your custom logic to calculate the processing time
        # Example: Assuming timestamps are in the format 'YYYY-MM-DD HH:mm:ss,SSSSSSS'
        sending_time = datetime.strptime(sending_timestamp, '%Y-%m-%d %H:%M:%S,%f')
        receiving_time = datetime.strptime(receiving_timestamp, '%Y-%m-%d %H:%M:%S,%f')
        processing_time = (receiving_time - sending_time).total_seconds()
        return processing_time


    def convert_im_ams_logs_to_json(self, sorted_im_ams_logs):
        logs_json = {}

        for log_entry in sorted_im_ams_logs:
            ixn_id = log_entry['ixnid']
            event_name = log_entry['event_name']
            timestamp = log_entry['timestamp']
            tenant_id = log_entry['tenant_id']

            if tenant_id not in logs_json:
                logs_json[tenant_id] = {}

            if ixn_id not in logs_json[tenant_id]:
                logs_json[tenant_id][ixn_id] = {'events': []}

            status = 'sending' if log_entry['arrow_direction'] == '->' else 'receiving'

            event_data = {
                'timestamp': timestamp,
                'agent_id': log_entry.get('agent_id', None),
                'arrow_direction': log_entry['arrow_direction'],
                'status': status,
                'header': self.parse_header(log_entry['header']),
            }

            logs_json[tenant_id][ixn_id]['events'].append({event_name: event_data})


        return logs_json

    def parse_header(self, header):
        # Your custom logic to parse the header and return a dictionary
        # Example: Assuming header is in the format 'key1:value1, key2:value2'
        header_parts = [part.strip() for part in header.split(',')]
        header_dict = {}
        for part in header_parts:
            key, value = part.split(':')
            header_dict[key.strip()] = value.strip()
        return header_dict


         


    def fetch_im_ams_sorted_logs(self,log_file, ixn=None):
        parsed_log_file = [self.parse_im_ams_logs(log, ixn) for log in log_file if self.parse_im_ams_logs(log,ixn) is not None]

        # Check if any logs were parsed
        if not parsed_log_file:
            # Handle the case when no logs were parsed
            return []

        sorted_logs = sorted(parsed_log_file, key=lambda x: (x['ixnid'], x['tenant_id'], x['timestamp'], x['event_name'], x['agent_id'] if x['agent_id'] is not None else 0))

        return sorted_logs

    def fetch_im_sfs_sorted_logs(self, log_file, ixn=None):
        parsed_log_file = [result for log in log_file if (result := self.parse_im_sfs_logs(log,ixn)) is not None]

        # Check if any logs were parsed
        if not parsed_log_file:
            # Handle the case when no logs were parsed
            return []

        sorted_logs = sorted(parsed_log_file, key=lambda x: (
            
            x['tenant_id'],
            x['ixnid'],
            x['timestamp'],
            x['event_name'],
            x['agent_id'],
            x['trunk_extension'],
            x['supervisor_id']

        ))


        # output_file_path='debug_output.log'
        # with open(output_file_path, 'w') as output_file:
        #      output_file.write(str(sorted_logs))

        


        return sorted_logs



    def fetch_im_ams_processing_details(self, paired_events):
        processing_details = {}

        for tenant_id, ixn_data in paired_events.items():
            for ixn_id, events in ixn_data.items():
                for event in events:
                    event_name, event_data = list(event.items())[0]
                    processing_time = event_data['processing_time'] * 1000  # Convert to milliseconds

                    # Initialize details if not present
                    if event_name not in processing_details:
                        processing_details[event_name] = {
                            'max_processing_time': float('-inf'),
                            'max_processing_time_ixn_id': None,
                            'max_processing_time_tenant_id': None,
                            'min_processing_time': float('inf'),
                            'min_processing_time_ixn_id': None,
                            'min_processing_time_tenant_id': None,
                            'total_processing_time': 0,
                            'event_count': 0
                        }

                    # Update maximum processing time
                    if processing_time > processing_details[event_name]['max_processing_time']:
                        processing_details[event_name]['max_processing_time'] = processing_time
                        processing_details[event_name]['max_processing_time_ixn_id'] = ixn_id
                        processing_details[event_name]['max_processing_time_tenant_id'] = tenant_id

                    # Update minimum processing time
                    if processing_time < processing_details[event_name]['min_processing_time']:
                        processing_details[event_name]['min_processing_time'] = processing_time
                        processing_details[event_name]['min_processing_time_ixn_id'] = ixn_id
                        processing_details[event_name]['min_processing_time_tenant_id'] = tenant_id

                    # Update total processing time and event count
                    processing_details[event_name]['total_processing_time'] += processing_time
                    processing_details[event_name]['event_count'] += 1

        # Calculate average processing time
        for event_name, details in processing_details.items():
            details['average_processing_time'] = (
                details['total_processing_time'] / details['event_count']
            ) if details['event_count'] > 0 else 0

        # Debugging print statements
        # print("Processing Details:")
        # print(json.dumps(processing_details, indent=2))

        return processing_details



    def file_upload_and_processing_logs(self):
        log_file = request.files['log_file']

        # Get the current working directory
        current_dir = os.getcwd()

        # Specify the directory for saving and reading files
        upload_dir = os.path.join(current_dir, 'logs_uploaded_files')
        
        # Ensure the directory exists
        os.makedirs(upload_dir, exist_ok=True)

        # Save uploaded files with absolute paths
        log_file_path = os.path.join(upload_dir, 'logfile.log')
        log_file.save(log_file_path)

        with open(log_file_path, 'r') as log_file:
            log_file =log_file.readlines()

        return log_file





    def parse_im_ams_logs(self,log, ixn=None):
        match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+) +\d+ +DEBUG: \[ {tenant:(\d+), ixn:(\d+)} \[im\.flow\] (<-|->) ams: (.+?)\]~~', log)

        if match:
            ixn_id = match.group(3)
            if ixn is None or ixn_id == str(ixn):
                timestamp = match.group(1)
                tenant_id = match.group(2)
                
                arrow_direction = match.group(4)
                
                # Check if there is a match for group(5)
                ams_data = match.group(5) if len(match.groups()) >= 5 else None


                # Use a regular expression to capture content inside parentheses and event name
                ams_match = re.search(r'(\w+) \((.*?)\)', ams_data)

                if ams_match:
                    ams_event_name = ams_match.group(1)
                    headers = ams_match.group(2)

                    # Extract ams_agent_id from headers
                    ams_agent_id_match = re.search(r'agent_id:(\d+)', headers)
                    ams_agent_id = ams_agent_id_match.group(1) if ams_agent_id_match else None



                output =  {
                    'timestamp': timestamp,
                    'tenant_id': int(tenant_id),
                    'ixnid': int(ixn_id),
                    'arrow_direction' : arrow_direction,
                    'event_name': ams_event_name,
                    'agent_id': int(ams_agent_id),
                    'header': headers,
                }
                return output


        return None


    def parse_im_sfs_logs(self, log, ixn=None):
        match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+) +\d+ +DEBUG: \[ {tenant:(\d+), ixn:(\d+)(?:, (agent|extrunk|supervisor): *(\d+))?} \[im\.flow\] (<-|->) client: (.+?)\]~~', log)

        if match:
            ixn_id = match.group(3)
            if ixn is None or ixn_id == str(ixn):
                timestamp = match.group(1)
                tenant_id = match.group(2)
                ixn_id = match.group(3)
                agent_type = match.group(4)
                if agent_type == 'agent':
                    agent_id = match.group(5) if match.group(5) else None
                    trunk_extension = None
                    supervisor_id = None
                elif agent_type == 'extrunk':
                    trunk_extension = match.group(5) if match.group(5) else None
                    agent_id = None
                    supervisor_id = None
                elif agent_type == 'supervisor':
                    supervisor_id = match.group(5) if match.group(5) else None
                    agent_id = None
                    trunk_extension = None
                else:
                    supervisor_id = None
                    agent_id = None
                    trunk_extension = None
                    
                arrow_direction = match.group(6)
                status = 'sending' if arrow_direction == '->' else 'receiving'

                # Check if there is a match for group(6)
                client_data = match.group(7) if len(match.groups()) >= 6 else None

                # Use a regular expression to capture content inside parentheses and event name
                client_match = re.search(r'(\w+) \((.*?)\)', client_data)

                if client_match:
                    client_event_name = client_match.group(1)
                    headers = client_match.group(2)
                    # Extract key-value pairs from the header string by splitting only the first colon
                    header_pairs = [pair.strip().split(':', 1) for pair in headers.split(',') if pair.strip() and not pair.strip().startswith('header:')]
                    header_obj = dict((key.strip(), value.strip()) for key, value in header_pairs)


                
                    output = {
                        'timestamp': timestamp,
                        'tenant_id': tenant_id,
                        'ixnid': ixn_id,
                        'agent_type':agent_type,
                        'agent_id': agent_id,
                        'trunk_extension': trunk_extension,
                        'supervisor_id': supervisor_id,
                        'arrow_direction': arrow_direction,
                        'event_name': client_event_name,
                        'status' : status,
                        'header': header_obj,
                    }
                    return output

        return None



    def write_IM_sorted_logs(self,file, sorted_logs, all_logs):
        prev_log = None  # To keep track of the previous log in the loop

        event_statistics = {}

        for log in sorted_logs:
        
            # Assuming log['timestamp'] and prev_log['timestamp'] are strings
            timestamp_format = "%Y-%m-%d %H:%M:%S,%f"

            # Calculate process time for related events
            if prev_log and prev_log['arrow_direction'] == '->' and log['ixnid'] == prev_log['ixnid'] and log['event_name'] == prev_log['event_name'] and log['agent_id'] == prev_log['agent_id'] and log['arrow_direction'] != prev_log['arrow_direction']:
                # Convert timestamp strings to datetime objects
                timestamp_log = datetime.strptime(log['timestamp'], timestamp_format)
                timestamp_prev_log = datetime.strptime(prev_log['timestamp'], timestamp_format)
                
                process_time = timestamp_log - timestamp_prev_log
                
                # Store event statistics
                event_name = log['event_name']
                if event_name not in event_statistics:
                    event_statistics[event_name] = []

                event_statistics[event_name].append(process_time.total_seconds() * 1000)
                # Print details in the desired format
                file.write(f"{prev_log['timestamp']} {prev_log['ixnid']}  DEBUG: [ {'im.flow'}] {prev_log['arrow_direction']} {'ams'}: {prev_log['header']}  (agent_id:{prev_log['agent_id']}) ]~~\n")
                file.write(f"{log['timestamp']} {log['ixnid']}  DEBUG: [ {'im.flow'}] {log['arrow_direction']} {'ams'}: {log['header']}  (agent_id:{log['agent_id']}) ]~~\n")
                file.write(f"    Event Name: {log['event_name']}\n")
                file.write(f"    Process Time: {process_time.total_seconds() * 1000:.3f} milliseconds\n")
                file.write(f"    Flow: { 'IM' } to { 'ams' }\n")
                file.write(f"    Tenant ID: {log['tenant_id']}\n")
                file.write(f"    IXN ID: {log['ixnid']}\n")
                file.write(f"    Agent ID: {log['agent_id']}\n\n")

                prev_log = None
            else:
                prev_log = log

        file.write("\n=== logs End ===\n")
        for log in all_logs:
            file.write(log)


        
        current_dir = os.getcwd()

       # Specify the output file for the event statistics with an absolute path
        event_stats_file = "ams_events_stats.txt"
        self.write_event_statistics(event_stats_file, event_statistics)

        # Get the absolute path of the output file
        output_file_path = "IM_ams_flow.log"

        # download the files (IM_ams_flow.log and event_stats.txt) as a zip
        file_paths = [output_file_path, event_stats_file]
        
        return self.download_files(file_paths, "Interaction_manager.zip")
        # download_name = "event_stats.log"
        # return download_file("event_stats.txt", download_name)

    def write_event_statistics(self,file, event_statistics):
        with open(file, 'w') as stats_file:
            stats_file.write("Event Statistics:\n\n")
            for event_name, times in event_statistics.items():
                if len(times) > 0:
                    avg_time = sum(times) / len(times)
                    min_time = min(times)
                    max_time = max(times)
                else:
                    avg_time = min_time = max_time = 0

                occurrence_count = len(times)
                stats_file.write(f"Event Name: {event_name}\n")
                stats_file.write(f"  Occurrence Count: {occurrence_count}\n")
                stats_file.write(f"  Average Processing Time: {avg_time:.3f} milliseconds\n")
                stats_file.write(f"  Minimum Processing Time: {min_time:.3f} milliseconds\n")
                stats_file.write(f"  Maximum Processing Time: {max_time:.3f} milliseconds\n\n")

    def download_files(self,file_paths, zip_name):
        # Create a BytesIO object to store the zip file
        buffer = io.BytesIO()

        # Write the files to the zip file in binary mode
        with zipfile.ZipFile(buffer, 'w') as zip_file:
            for file_path in file_paths:

                # Add the file to the zip file
                zip_file.write(file_path, arcname=file_path)

        # Seek to the beginning of the buffer
        buffer.seek(0)

        # Return the zip file as a downloadable file
        return send_file(buffer, as_attachment=True, download_name=zip_name)