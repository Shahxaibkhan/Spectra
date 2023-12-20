# se_page.py

from flask import Flask, render_template, request, send_file
import io
import os
import zipfile
import re
from datetime import datetime
import json
from .base_page import BasePage

class SEPage(BasePage):

    def __init__(self, app):
        self.app = app


    def analyze(self):
        # Implement IM analysis logic here
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
    
    def display_checks_stats(self):
        checks_stats = self.generate_checks()

        # Return the generated statistics to be displayed in the HTML template
        return render_template('checks_stats.html', checks_stats=checks_stats)



    def generate_se_stats(self):
        # Generate summary report
        summary_report = self.generate_summary_report()

        # Return the generated summary report to be displayed in the HTML template
        return render_template('vector_stats.html', summary_report=summary_report)

    def generate_summary_report(self):
        log_file = self.file_upload_and_processing_logs()
        vector_stats = self.generate_vector_stats(log_file)
        check_results = self.generate_checks(log_file)

        print('check_results: ', check_results)

        # Process results for summary report
        total_calls = len(vector_stats)

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

        # Extract vectors loaded and compilation time from check_results
        vectors_loaded = 0
        compilation_time = 0

        for check_result in check_results:
            if check_result["check_name"] == "Vector Loaded and Compilation Time":
                vectors_loaded = check_result["vectors_loaded"]
                compilation_time = check_result["compilation_time"]
                break

        summary_report = {
            "total_calls": total_calls,
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
            "vector_id_counts": vector_id_counts
        }

        print('Summary Report:', summary_report)
        return summary_report


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

                

                # Break the loop after the first match is found
                break
        print('vector_stats:',vector_stats)
        return vector_stats


    def generate_vector_stats(self,log_file):
        # Get processed logs
        sorted_logs = self.vectors_processed_logs(log_file)

        vector_stats = []

        # Create a dictionary to store vector statistics
        vector_statistics = {}

        for log in sorted_logs:
            key = f"{log['call_id']}_{log['vector_id']}"
            
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

        # Convert the dictionary to a JSON object
        logs_json = json.dumps(logs_by_call_vector, indent=2)

        return logs_json


    def vectors_processed_logs(self,log_file):
            

            parsed_vector_logs = [result for log in log_file if (result := self.parse_vector_log(log)) is not None]

            # Check if any logs were parsed
            if not parsed_vector_logs:
                # Handle the case when no logs were parsed
                return []

            sorted_logs = sorted(parsed_vector_logs, key=lambda x: (x['call_id'],x['vector_id'], x['timestamp'], x['execution_index'], x['tenant_id']))

            
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



    def parse_vector_log(self,log):
            search_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[\d+\]  DEBUG: \[ VectorScript::executeVectorSteps: > Time taken for script execution:(\d+) usecs\. CallID:(\d+\|\d+\.\d+\.\d+), VecID:(\d+\|\d+\.\d+\.\d+), isLastStep:(true|false), executionIndex:(\d+) \]~~'
            log_pattern = re.compile(search_pattern)
            logpattern_match = log_pattern.search(log)

            if logpattern_match:
                result = {}  # Object to store the extracted values

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


                print("match result:",result)
                return result

            # If no match is found, return None'
            return None




    