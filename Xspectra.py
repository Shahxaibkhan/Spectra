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



app = Flask(__name__)

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
    # button_pressed = request.form.get('button')  # Assuming 'button' is the name attribute in the HTML
    
    if lab == 'YODA':
        host = '172.16.19.137'

    if action == 'SE Logs':
        return se_page.fetch_and_analyze_se_logs(host,logs_path,username,password) 
        
   

if __name__ == '__main__':
    app.run(debug=True, port=1000)