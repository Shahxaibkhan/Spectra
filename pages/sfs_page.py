# se_page.py

from flask import Flask, render_template, request, send_file
import io
import os
import zipfile
import re
from datetime import datetime
import json
from .base_page import BasePage

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



    def generate_sfs_stats(self):
        # Generate summary report
        summary_report = self.generate_summary_report()

        # Return the generated summary report to be displayed in the HTML template
        return render_template('vector_stats.html', summary_report=summary_report)




    
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

           

    def extract_tenant_ixn_from_log(self,log):
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

    def parse_trace_log(self,log, session_id_details):
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




    