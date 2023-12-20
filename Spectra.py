from flask import Flask, render_template, request, send_file
import io
import os
import zipfile
import re
from datetime import datetime
from pages.im_page import IMPage
from pages.se_page import SEPage
from pages.sfs_page import SFSPage



app = Flask(__name__)

im_page = IMPage(app)
se_page = SEPage(app)
sfs_page = SFSPage(app)



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

def parse_sfs_log(log):
    match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+).*tenant_id: (\d+).*ixn_id: (\d+).*', log)
    if match:
        timestamp = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S,%f')
        tenant_id = int(match.group(2))
        ixn_id = int(match.group(3))
        return timestamp, 'SFS', tenant_id, ixn_id, log  # Adjusted the return statement
    return None, None, None, None, log  # Ensure five values are returned for consistency


def parse_se_log(log, se_logs_dict):
    match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+).*ScriptExecutor::processCallQueue > RECEIVED new CallID:\d+\|(\d+\.\d+\.\d+).*', log)
    if match:
        timestamp = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S,%f')
        event_info = match.group(2)

        # Extract tenant id and ixn id from the event_info
        tenant_id = int(event_info.split('.')[0])
        ixn_id = int(event_info.split('.')[2])

        if tenant_id not in se_logs_dict:
            se_logs_dict[tenant_id] = {}

        if ixn_id not in se_logs_dict[tenant_id] or timestamp < se_logs_dict[tenant_id][ixn_id][0]:
            se_logs_dict[tenant_id][ixn_id] = (timestamp, 'SE', tenant_id, ixn_id, log)

        # Return the parsed values
        return timestamp, 'SE', tenant_id, ixn_id, log

    # Return None values if no match is found
    return None, None, None, None, log

def write_sorted_sfs_se_logs(file, sorted_logs, all_logs):
    prev_log = None  # To keep track of the previous log in the loop

    event_statistics = {'Interaction added': []} 

    for log in sorted_logs:
        # Calculate process time for related events
        if prev_log and log[3] == prev_log[3] and log[2] == prev_log[2] and log[1] != prev_log[1]:
            process_time = log[0] - prev_log[0]
            
            event_name = "Interaction added"
            event_statistics[event_name].append(process_time.total_seconds() * 1000)

            # Print details in the desired format
            file.write(f"\n{prev_log[0]} {prev_log[3]} {prev_log[1]} {prev_log[4]}")
            file.write(f"{log[0]} {log[3]} {log[1]} {log[4]} \n")
            file.write(f"    Process Time: {process_time.total_seconds() * 1000:.3f} milliseconds\n")
            file.write(f"    Flow: {prev_log[1]} to {log[1]}\n")
            file.write(f"    Tenant ID: {log[2]}\n")
            file.write(f"    IXN ID: {log[3]}\n")

            prev_log = None
        else:
            prev_log = log

    file.write("\n=== logs End ===\n")
    for log in all_logs:
        file.write(log)


    current_dir = os.getcwd()

    # Specify the output file for the event statistics with an absolute path
    event_stats_file = "sfs_se_event_stats.txt"
    write_event_statistics(event_stats_file, event_statistics)

    # Get the absolute path of the output file
    output_file_path = "SFS-SE_flow.log"

    # download the files (SFS-SE_flow.log and sfs_se_event_stats.txt) as a zip
    file_paths = [output_file_path, event_stats_file]
     
    return download_files(file_paths, "sfs-se.zip")


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
    event_stats_file = "sfs_im_event_stats.txt"
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




def files_upload_and_processing():
    sfs_file = request.files['sfs_file']
    im_file = request.files['im_file']

    # Get the current working directory
    current_dir = os.getcwd()

    # Specify the directory for saving and reading files
    upload_dir = os.path.join(current_dir, 'sfs_im_uploaded_files')
    
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
    
def files_upload_and_processing_sfs_se_logs():
    sfs_file = request.files['sfs_file']
    se_file = request.files['se_file']

    # Get the current working directory
    current_dir = os.getcwd()

    # Specify the directory for saving and reading files
    upload_dir = os.path.join(current_dir, 'sfs_se_uploaded_files')
    
    # Ensure the directory exists
    os.makedirs(upload_dir, exist_ok=True)

    # Save uploaded files with absolute paths
    sfs_file_path = os.path.join(upload_dir, 'SFS.log')
    se_file_path = os.path.join(upload_dir, 'SE.log')
    sfs_file.save(sfs_file_path)
    se_file.save(se_file_path)

    with open(sfs_file_path, 'r') as sfs_file, open(se_file_path, 'r') as se_file:
        sfs_logs = sfs_file.readlines()
        se_logs = se_file.readlines()

    parsed_sfs_logs = [parse_sfs_log(log) for log in sfs_logs]

    # Dictionary to store SE logs based on tenant_id and ixn_id
    se_logs_dict = {}
    for log in se_logs:
        parse_se_log(log, se_logs_dict)

    # Filter out logs where timestamp is None
    sorted_logs = sorted(filter(lambda x: x[0] is not None, parsed_sfs_logs + [log for logs in se_logs_dict.values() for log in logs.values()]), key=lambda x: (x[0], x[2], x[3], x[1]))

    return sorted_logs




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
                min_processing_time = float(lines[i + 3].split(":")[1].strip().split()[0])
                max_processing_time = float(lines[i + 4].split(":")[1].strip().split()[0])

                event_stats = {
                    'occurrence_count': occurrence_count,
                    'avg_processing_time': avg_processing_time,
                    'min_processing_time': min_processing_time,
                    'max_processing_time': max_processing_time,
                }

                event_statistics[event_name] = event_stats
                i += 5
            else:
                i += 1

    return event_statistics





# =========================================================================================================================   ROUTES  ============================================================================================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze/sfs-im')
def analyze_sfsim():
    # Implement your SFS analysis logic here
    return render_template('sfsim.html')  

@app.route('/analyze/sfs-se')
def analyze_sfsse():
    return render_template('sfsse.html')  

@app.route('/analyze/im')
def analyze_im():
    # Implement your IM analysis logic here
    return im_page.analyze() 

@app.route('/analyze/se')
def analyze_se():
    return se_page.analyze() 

@app.route('/analyze/sfs')
def analyze_sfs():
    return sfs_page.analyze() 

@app.route('/logs')
def analyze_logs():
    # Implement your IM analysis logic here
   return render_template('logs_extractor.html')

@app.route('/add_file', methods=['POST'])
def add_file():
    global log_files
    file = request.files['file']
    log_files.append(file)
    return '', 204

@app.route('/extract_logs', methods=['POST'])
def extract_logs():
    global log_files

    selected_log_type = request.form['logType']
    logs = []

    for file in log_files:
        content = file.stream.read().decode('utf-8')
        lines = content.split('\n')

        for line in lines:
            if selected_log_type in line:
                logs.append(line)

    logs.sort(key=lambda x: x.split(' ')[0])

    merged_logs = '\n'.join(logs)

    output = StringIO()
    output.write(merged_logs)
    output.seek(0)

    return send_file(output, as_attachment=True, download_name='merged_logs.txt')


@app.route('/upload-sfsse', methods=['POST'])
def upload_sfsse():
    sorted_logs = files_upload_and_processing_sfs_se_logs()
    current_dir = os.getcwd()
     # Specify the output file for the analysis with an absolute path
    output_file = os.path.join(current_dir, "SFS-SE_flow.log")
    with open(output_file, 'w') as file:
        return write_sorted_sfs_se_logs(file, sorted_logs, [])

@app.route('/upload-im', methods=['POST'])
def upload_im():
     return im_page.upload_im() 

@app.route('/display_se_report', methods=['POST'])
def upload_se():
    action = request.form['action']
    if action == 'Analyze Vectors':
        return se_page.analyze_vectors() 
    elif action == 'Display Report':
        return se_page.generate_se_stats()
    # elif action == 'Run Checks':
    #     return se_page.display_checks_stats()
    
@app.route('/display_sfs_report', methods=['POST'])
def upload_sfs():
    action = request.form['action']
    print(action)
    if action == 'Analyze Worker threads':
        return sfs_page.analyze_wrkr_threads() 
    elif action == 'Display Report':
        return sfs_page.generate_sfs_stats()
    # elif action == 'Run Checks':
    #     return se_page.display_checks_stats()
     

@app.route('/upload-sfsim', methods=['POST'])
def upload_sfsim():
    sorted_logs = files_upload_and_processing()
    current_dir = os.getcwd()
     # Specify the output file for the analysis with an absolute path
    output_file = os.path.join(current_dir, "SFS-IM_flow.log")
    with open(output_file, 'w') as file:
        return write_sorted_logs(file, sorted_logs, [])




@app.route('/plot-sfs-im', methods=['GET'])
def plot_sfs_im_results():
    # Read event statistics from the file
    event_stats_file_path = os.path.join(os.getcwd(), 'sfs_im_event_stats.txt')
    event_statistics = read_event_statistics(event_stats_file_path)

    # Render the template with the plot file path and event statistics
    return render_template('plot.html',  event_statistics=event_statistics)

@app.route('/plot-sfs-se', methods=['GET'])
def plot_sfs_se_results():
    # Read event statistics from the file
    event_stats_file_path = os.path.join(os.getcwd(), 'sfs_se_event_stats.txt')
    event_statistics = read_event_statistics(event_stats_file_path)

    # Render the template with the plot file path and event statistics
    return render_template('plot.html',  event_statistics=event_statistics)

@app.route('/plot-im_ams', methods=['GET'])
def plot_im_ams_results():
    # Read event statistics from the file
    event_stats_file_path = os.path.join(os.getcwd(), 'ams_events_stats.txt')
    event_statistics = read_event_statistics(event_stats_file_path)

    # Render the template with the plot file path and event statistics
    return render_template('plot.html',  event_statistics=event_statistics)


if __name__ == '__main__':
    app.run(port=3001)