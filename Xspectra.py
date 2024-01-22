from flask import Flask, render_template, request, send_file
import io
import os
import zipfile
import re
from datetime import datetime
from pages.im_page import IMPage
from pages.se_page import SEPage
from pages.sfs_page import SFSPage
from pages.ssh_handler import fetch_log_files

import configparser

app = Flask(__name__)

# Load the config file
config = configparser.ConfigParser()
config.read('config.ini')


im_page = IMPage(app)
se_page = SEPage(app)
sfs_page = SFSPage(app)




# =========================================================================================================================   ROUTES  ============================================================================================================================================

@app.route('/')
def index():
    return render_template('xspectra.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    lab = request.form.get('labSelect')
    logs_path = request.form.get('LogsPath')
    username = request.form.get('username')
    password = request.form.get('password')

    print("lab", lab)
    print("logs_path", logs_path)
    print("username", username)
    print("password", password)
    action = request.form['action']
    print(action)

    # Fetch the IPs from the config file based on the lab
    primary_ip = config.get(lab, 'primary_ip')
    secondary_ip = config.get(lab, 'secondary_ip')

     # Check the selected radio button
    scenario = request.form.get('Scenario')
    print(scenario)
    print(primary_ip)
    # Determine which IPs to fetch based on the selected scenario
    selected_ips = []
    if scenario == 'Primary':
        selected_ips.append(primary_ip)
    elif scenario == 'Secondary':
        selected_ips.append(secondary_ip)
    elif scenario == 'HA Scenario':
        selected_ips.extend([primary_ip, secondary_ip])

    print(selected_ips)
    if action == 'SE Logs':
        return se_page.fetch_and_analyze_se_logs(selected_ips, logs_path, username, password)
    if action == 'SFS Logs':
        return sfs_page.fetch_and_analyze_sfs_logs(selected_ips, logs_path, username, password)

if __name__ == '__main__':
    app.run(debug=True, port=1000)