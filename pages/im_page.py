# im_page.py

from flask import Flask, render_template, request, send_file
import io
import os
import zipfile
import re
from datetime import datetime
from .base_page import BasePage

class IMPage(BasePage):

    def __init__(self, app):
        self.app = app


    def analyze(self):
        # Implement IM analysis logic here
        return render_template('im.html')


    def upload_im(self):
        sorted_logs = self.file_upload_and_processing_im_logs()
        current_dir = os.getcwd()
        # Specify the output file for the analysis with an absolute path
        output_file = os.path.join(current_dir, "IM_ams_flow.log")
        with open(output_file, 'w') as file:
            return self.write_IM_sorted_logs(file, sorted_logs, [])



    def file_upload_and_processing_im_logs(self):
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

        parsed_log_file = [self.parse_im_log(log) for log in log_file if self.parse_im_log(log) is not None]

        # Check if any logs were parsed
        if not parsed_log_file:
            # Handle the case when no logs were parsed
            return []

        sorted_logs = sorted(parsed_log_file, key=lambda x: (x['ixnid'], x['event_name'], x['agent_id'] if x['agent_id'] is not None else 0, x['tenant_id'], x['timestamp']))

        return sorted_logs


    def parse_im_log(self,log):
        match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+) +\d+ +DEBUG: \[ {tenant:(\d+), ixn:(\d+)} \[im\.flow\] (<-|->) ams: (.+?)\]~~', log)

        if match:
            timestamp = match.group(1)
            tenant_id = match.group(2)
            ixn_id = match.group(3)
            arrow_direction = match.group(4)
            
            # Check if there is a match for group(5)
            ams_data = match.group(5) if len(match.groups()) >= 5 else None


            ams_match = re.search(r'(\w+) \(agent_id:(\d+)', ams_data)
            ams_event_name = ams_match.group(1)
            ams_agent_id = ams_match.group(2)

            output =  {
                'timestamp': datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S,%f"),
                'tenant_id': int(tenant_id),
                'ixnid': int(ixn_id),
                'arrow_direction' : arrow_direction,
                'event_name': ams_event_name,
                'agent_id': int(ams_agent_id),
                'header': ams_data,
            }
            return output


        return None

    def write_IM_sorted_logs(self,file, sorted_logs, all_logs):
        prev_log = None  # To keep track of the previous log in the loop

        event_statistics = {}

        for log in sorted_logs:
        

            # Calculate process time for related events
            if prev_log and prev_log['arrow_direction'] == '->' and log['ixnid'] == prev_log['ixnid'] and log['event_name'] == prev_log['event_name'] and log['agent_id'] == prev_log['agent_id'] and log['arrow_direction'] != prev_log['arrow_direction']:
                process_time = log['timestamp'] - prev_log['timestamp']
                
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