from flask import Flask, render_template, request, send_file
import io  # Add this line
import matplotlib.pyplot as plt
import zipfile
from datetime import datetime
app = Flask(__name__)


import re
from datetime import datetime, timedelta

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

# def write_sorted_logs(file, sorted_logs, all_logs):
#     prev_log = None  # To keep track of the previous log in the loop
#     for log in sorted_logs:
#         # Calculate process time for related events
#         if prev_log and log['ixn'] == prev_log['ixn'] and log['event_name'] == prev_log['event_name'] and log['agent_id'] == prev_log['agent_id'] and log['arrow'] != prev_log['arrow'] and log['flow_type'] != prev_log['flow_type']:
#             process_time = log['timestamp'] - prev_log['timestamp']
#             file.write(f"{prev_log['timestamp']} {prev_log['ixn']}    DEBUG: [ {prev_log['flow_type']}] {prev_log['arrow']} {prev_log['interaction_type']}: {prev_log['event_name']} {prev_log['event_header']} (agent_id:{prev_log['agent_id']}) ]~~\n")
#             file.write(f"{log['timestamp']} {log['ixn']}    DEBUG: [ {log['flow_type']}] {log['arrow']} {log['interaction_type']}: {log['event_name']} {log['event_header']} (agent_id:{log['agent_id']}) ]~~\n")
#             # Print details in the desired format
#             file.write(f"    Event Name: {log['event_name']}\n")
#             file.write(f"    Process Time: {process_time.total_seconds() * 1000:.3f} milliseconds\n")
#             file.write(f"    Flow: {prev_log['flow_type'].replace('.flow', '').upper()} to {log['flow_type'].replace('.flow', '').upper()}\n")
#             file.write(f"    Tenant ID: {log['tenant_id']}\n")
#             file.write(f"    IXN ID: {log['ixn']}\n")
#             file.write(f"    Agent ID: {log['agent_id']}\n\n")
#             prev_log = None
#         else:   
#             prev_log = log

#     file.write("\n=== logs End ===\n")
#     for log in all_logs:
#         file.write(log)


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




def pair_logs(logs):
    paired_logs = []
    unpaired_logs = []

    for log in logs:
        if log['event_name'] == 'Assign':
            paired_logs.append({'start': log, 'end': None})
        elif log['event_name'] == 'Assigned':
            if paired_logs and paired_logs[-1]['start']['ixn'] == log['ixn'] and paired_logs[-1]['start']['agent_id'] == log['agent_id']:
                paired_logs[-1]['end'] = log
            else:
                unpaired_logs.append(log)
        else:
            unpaired_logs.append(log)

        if log['event_name'] == 'Provision':
            paired_logs.append({'start': log, 'end': None})
        elif log['event_name'] == 'Provisioned':
            if paired_logs and paired_logs[-1]['start']['ixn'] == log['ixn'] and paired_logs[-1]['start']['agent_id'] == log['agent_id']:
                paired_logs[-1]['end'] = log
            else:
                unpaired_logs.append(log)
        else:
            unpaired_logs.append(log)


        if log['event_name'] == 'Route':
            paired_logs.append({'start': log, 'end': None})
        elif log['event_name'] == 'Routed':
            if paired_logs and paired_logs[-1]['start']['ixn'] == log['ixn'] and paired_logs[-1]['start']['agent_id'] == log['agent_id']:
                paired_logs[-1]['end'] = log
            else:
                unpaired_logs.append(log)
        else:
            unpaired_logs.append(log)

        if log['event_name'] == 'Terminate':
            paired_logs.append({'start': log, 'end': None})
        elif log['event_name'] == 'Terminated':
            if paired_logs and paired_logs[-1]['start']['ixn'] == log['ixn'] and paired_logs[-1]['start']['agent_id'] == log['agent_id']:
                paired_logs[-1]['end'] = log
            else:
                unpaired_logs.append(log)
        else:
            unpaired_logs.append(log)

    return paired_logs, unpaired_logs

def write_sorted_sfs_logs(file, sorted_logs, all_logs):
    paired_logs, unpaired_logs = pair_logs(sorted_logs)

    # Write paired logs
    for pair in paired_logs:
        start_log = pair['start']
        end_log = pair['end']
        process_time = end_log['timestamp'] - start_log['timestamp']

        file.write(f"{start_log['timestamp']} {start_log['ixn']}    DEBUG: [ {start_log['flow_type']}] {start_log['arrow']} {start_log['interaction_type']}: {start_log['event_name']} {start_log['event_header']} (agent_id:{start_log['agent_id']}) ]~~\n")
        file.write(f"{end_log['timestamp']} {end_log['ixn']}    DEBUG: [ {end_log['flow_type']}] {end_log['arrow']} {end_log['interaction_type']}: {end_log['event_name']} {end_log['event_header']} (agent_id:{end_log['agent_id']}) ]~~\n")

        # Print details in the desired format
        file.write(f"    Event Name: {start_log['event_name']}\n")
        file.write(f"    Process Time: {process_time.total_seconds() * 1000:.3f} milliseconds\n")
        file.write(f"    Flow: {start_log['flow_type'].replace('.flow', '').upper()} to {end_log['flow_type'].replace('.flow', '').upper()}\n")
        file.write(f"    Tenant ID: {start_log['tenant_id']}\n")
        file.write(f"    IXN ID: {start_log['ixn']}\n")
        file.write(f"    Agent ID: {start_log['agent_id']}\n\n")

    # Write unpaired logs
    # for log in unpaired_logs:
    #     file.write(f"{log['timestamp']} {log['ixn']}    DEBUG: [ {log['flow_type']}] {log['interaction_type']}: {log['event_name']} {log['event_header']} (agent_id:{log['agent_id']}) ]~~\n")

    file.write("\n=== logs End ===\n")
    for log in all_logs:
        file.write(log)

import os

# ... (your existing code) ...

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


# ... (your existing code) ...



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
    
   

@app.route('/download')



# Add a new route for plotting
@app.route('/plot', methods=['GET'])
def plot_results():
    # Call your existing functions to process logs
    sfs_logs = read_and_extract('uploaded_files/SFS.log')
    im_logs = read_and_extract('uploaded_files/IM.log')
    unified_logs = sfs_logs + im_logs
    sorted_logs = sorted(unified_logs, key=lambda x: (x['ixn'], x['event_name'], x['agent_id'] if x['agent_id'] is not None else 0, x['timestamp']))

    # Generate event statistics
    event_statistics = generate_event_statistics(sorted_logs)

    # Plot event statistics
    plot_event_statistics(event_statistics)

    return "Event Statistics plotted successfully!"

# # Function to generate event statistics
# def generate_event_statistics(sorted_logs):
#     event_statistics = {}

#     for log in sorted_logs:
#         event_name = log['event_name']
#         if event_name not in event_statistics:
#             event_statistics[event_name] = []

#         event_statistics[event_name].append(log['timestamp'])

#     return event_statistics

# # Function to plot event statistics
# def plot_event_statistics(event_statistics):
#     # Calculate statistics for plotting
#     event_names = list(event_statistics.keys())
#     occurrence_counts = [len(times) for times in event_statistics.values()]
#     avg_processing_times = [np.mean(np.diff(times)) * 1000 if len(times) > 1 else 0 for times in event_statistics.values()]

#     # Plot bar chart
#     plt.figure(figsize=(12, 6))
#     plt.bar(event_names, occurrence_counts, color='b', alpha=0.7, label='Occurrence Count')
#     plt.bar(event_names, avg_processing_times, color='r', alpha=0.7, label='Average Processing Time (ms)')
#     plt.title('Event Statistics')
#     plt.xlabel('Event Name')
#     plt.ylabel('Count / Average Processing Time (ms)')
#     plt.xticks(rotation=45, ha='right')
#     plt.legend()
#     plt.tight_layout()
#     plt.savefig('static/event_statistics_plot.png')  # Save the plot to a static file

#     return "Results plotted successfully!"


if __name__ == '__main__':
    app.run(port=3000)