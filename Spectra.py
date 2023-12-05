from flask import Flask, render_template, request, send_file
import io
import os
import zipfile
import re
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np



app = Flask(__name__)



def extract_info(log,pattern):
   
    match = re.search(pattern,log)
    if match:
        timestamp_str, ix, tenant_id, ixn, agent_id, flow_type, arrow, interaction_type, event_info = match.groups()

        # Use a regex to capture the event name and headers
        event_match = re.search(r'(\w+) \((.*?)\)', event_info)
        event_name = event_match.group(1) if event_match else "Unknown"
        event_header = event_match.group(2) if event_match else ""

        return {
            'timestamp': datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f"),
            'ix': int(ix),
            'tenant_id': int(tenant_id),
            'ixn': int(ixn),
            'agent_id': int(agent_id) if agent_id else None,
            'flow_type': flow_type,
            'arrow': arrow,
            'interaction_type': interaction_type,
            'event_name': event_name,
            'event_header': event_header,
        }
        
    return None

def read_and_extract(file_path,log_flow = None):
    logs = []
    if log_flow == None:
        pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{6})\s+(\d+)\s+DEBUG: \[ {tenant:(\d+), ixn:(\d+)(?:, agent:(\d+))?} \[(SFS.flow|im.flow)] (->|<-) (im|client): (.+?) \]~~'
    if log_flow =="SFS.flow":
        pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{6})\s+(\d+)\s+DEBUG: \[ {tenant:(\d+), ixn:(\d+)(?:, agent:(\d+))?} \[(SFS\.flow)] (->|<-) (im): (.+?) \]~~'

    with open(file_path, 'r') as file:
        for line in file:
            info = extract_info(line,pattern)
            if info:
                logs.append(info)
    return logs



def write_sorted_logs(file, sorted_logs, all_logs):
    prev_log = None  # To keep track of the previous log in the loop

    event_statistics = {}

    for log in sorted_logs:
        # Calculate process time for related events
        if prev_log and log['ixn'] == prev_log['ixn'] and log['event_name'] == prev_log['event_name'] and log['agent_id'] == prev_log['agent_id'] and log['arrow'] != prev_log['arrow'] and log['flow_type'] != prev_log['flow_type']:
            process_time = log['timestamp'] - prev_log['timestamp']
            
            # Store event statistics
            event_name = log['event_name']
            if event_name not in event_statistics:
                event_statistics[event_name] = []

            event_statistics[event_name].append(process_time.total_seconds() * 1000)

            # Print details in the desired format
            file.write(f"{prev_log['timestamp']} {prev_log['ixn']}    DEBUG: [ {prev_log['flow_type']}] {prev_log['arrow']} {prev_log['interaction_type']}: {prev_log['event_name']} {prev_log['event_header']} (agent_id:{prev_log['agent_id']}) ]~~\n")
            file.write(f"{log['timestamp']} {log['ixn']}    DEBUG: [ {log['flow_type']}] {log['arrow']} {log['interaction_type']}: {log['event_name']} {log['event_header']} (agent_id:{log['agent_id']}) ]~~\n")
            file.write(f"    Event Name: {log['event_name']}\n")
            file.write(f"    Process Time: {process_time.total_seconds() * 1000:.3f} milliseconds\n")
            file.write(f"    Flow: {prev_log['flow_type'].replace('.flow', '').upper()} to {log['flow_type'].replace('.flow', '').upper()}\n")
            file.write(f"    Tenant ID: {log['tenant_id']}\n")
            file.write(f"    IXN ID: {log['ixn']}\n")
            file.write(f"    Agent ID: {log['agent_id']}\n\n")

            prev_log = None
        else:
            prev_log = log

    file.write("\n=== logs End ===\n")
    for log in all_logs:
        file.write(log)

    current_dir = os.getcwd()

   # Specify the output file for the event statistics with an absolute path
    event_stats_file = "event_stats.txt"
    write_event_statistics(event_stats_file, event_statistics)

    # Get the absolute path of the output file
    output_file_path = "SFS-IM_flow.log"

    # download the files (SFS-IM_flow.log and event_stats.txt) as a zip
    file_paths = [output_file_path, event_stats_file]
     
    return download_files(file_paths, "sfs-im.zip")
    # download_name = "event_stats.log"
    # return download_file("event_stats.txt", download_name)


def write_event_statistics(file, event_statistics):
    with open(file, 'w') as stats_file:
        stats_file.write("Event Statistics:\n\n")
        for event_name, times in event_statistics.items():
            avg_time = sum(times) / len(times) if len(times) > 0 else 0
            occurrence_count = len(times)
            stats_file.write(f"Event Name: {event_name}\n")
            stats_file.write(f"  Occurrence Count: {occurrence_count}\n")
            stats_file.write(f"  Average Processing Time: {avg_time:.3f} milliseconds\n\n")



def files_upload_and_processing():
    sfs_file = request.files['sfs_file']
    im_file = request.files['im_file']

    # Get the current working directory
    current_dir = os.getcwd()

    # Specify the directory for saving and reading files
    upload_dir = os.path.join(current_dir, 'uploaded_files')
    
    # Ensure the directory exists
    os.makedirs(upload_dir, exist_ok=True)

    # Save uploaded files with absolute paths
    sfs_file.save(os.path.join(upload_dir, 'SFS.log'))
    im_file.save(os.path.join(upload_dir, 'IM.log'))

    # Call your existing functions with the uploaded files
    sfs_logs = read_and_extract(os.path.join(upload_dir, 'SFS.log'))
    im_logs = read_and_extract(os.path.join(upload_dir, 'IM.log'))
    unified_logs = sfs_logs + im_logs
    return sorted(unified_logs, key=lambda x: (x['ixn'], x['event_name'], x['agent_id'] if x['agent_id'] is not None else 0, x['timestamp']))
    
   

def download_files(file_paths, zip_name):
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

def read_event_statistics(file_path):
    event_statistics = {}

    with open(file_path, 'r') as stats_file:
        lines = stats_file.readlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("Event Name:"):
                event_name = line.split(":")[1].strip()
                occurrence_count = int(lines[i + 1].split(":")[1].strip())
                avg_processing_time = float(lines[i + 2].split(":")[1].strip().split()[0])
                event_statistics[event_name] = {'occurrence_count': occurrence_count, 'avg_processing_time': avg_processing_time}
                i += 3
            else:
                i += 1

    return event_statistics



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze/sfs')
def analyze_sfs():
    # Implement your SFS analysis logic here
    return render_template('sfs.html')  # Replace 'sfs.html' with the actual template for SFS analysis

@app.route('/analyze/im')
def analyze_im():
    # Implement your IM analysis logic here
    return render_template('im.html')  # Replace 'im.html' with the actual template for IM analysis


@app.route('/upload', methods=['POST'])
def upload():
    sorted_logs = files_upload_and_processing()
    current_dir = os.getcwd()
     # Specify the output file for the analysis with an absolute path
    output_file = os.path.join(current_dir, "SFS-IM_flow.log")
    with open(output_file, 'w') as file:
        return write_sorted_logs(file, sorted_logs, [])

@app.route('/plot', methods=['GET'])
def plot_results():
    # Read event statistics from the file
    event_stats_file_path = os.path.join(os.getcwd(), 'event_stats.txt')
    event_statistics = read_event_statistics(event_stats_file_path)

    # Render the template with the plot file path and event statistics
    return render_template('plot.html',  event_statistics=event_statistics)


if __name__ == '__main__':
    app.run(port=3001)