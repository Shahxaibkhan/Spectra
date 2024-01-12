# im_page.py

from flask import Flask, render_template, request, send_file
import io
import os
import zipfile
import re
from datetime import datetime
from .base_page import BasePage
import json

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
    #     return render_template('im_stats.html', summary_report=summary_report)

    def upload_im(self):
        log_file = self.file_upload_and_processing_logs()
        sorted_im_ams_logs = self.fetch_im_ams_logs(log_file)
        current_dir = os.getcwd()
        # Specify the output file for the analysis with an absolute path
        output_file = os.path.join(current_dir, "IM_ams_flow.log")
        with open(output_file, 'w') as file:
            return self.write_IM_sorted_logs(file, sorted_im_ams_logs, [])

    def generate_im_stats(self):
        # Generate summary report
        log_file = self.file_upload_and_processing_logs()
        sorted_im_ams_logs = self.fetch_im_ams_logs(log_file)
        # Convert logs to JSON
        logs_json = self.convert_im_ams_logs_to_json(sorted_im_ams_logs)
        

        summary_data = self.generate_summary_report(logs_json)

        # Return the generated summary report and detailed summary to be displayed in the HTML template
        return render_template(
            'im_stats.html',
            im_ams_event_details=summary_data['im_ams_event_details'],
            im_ams_processing_details=summary_data['im_ams_processing_details']
        )


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

        # jsonLogs = json.dumps(result_data, indent=2)
        # output_file_path = "custom_output.json"
        # with open(output_file_path, 'w') as output_file:
        #     output_file.write(jsonLogs)
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


         


    def fetch_im_ams_logs(self,log_file):
        parsed_log_file = [self.parse_im_ams_logs(log) for log in log_file if self.parse_im_ams_logs(log) is not None]

        # Check if any logs were parsed
        if not parsed_log_file:
            # Handle the case when no logs were parsed
            return []

        sorted_logs = sorted(parsed_log_file, key=lambda x: (x['ixnid'], x['event_name'], x['agent_id'] if x['agent_id'] is not None else 0, x['tenant_id'], x['timestamp']))

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
        print("Processing Details:")
        print(json.dumps(processing_details, indent=2))

        return processing_details



    def generate_summary_report(self,logs):
        im_ams_event_details = self.fetch_im_ams_event_details(logs)
        im_ams_processing_details = self.fetch_im_ams_processing_details(im_ams_event_details['paired_events'])

        summary_data = {
        'im_ams_event_details': im_ams_event_details,
        'im_ams_processing_details': im_ams_processing_details
        }

        return summary_data

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





    def parse_im_ams_logs(self,log):
        match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+) +\d+ +DEBUG: \[ {tenant:(\d+), ixn:(\d+)} \[im\.flow\] (<-|->) ams: (.+?)\]~~', log)

        if match:
            timestamp = match.group(1)
            tenant_id = match.group(2)
            ixn_id = match.group(3)
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