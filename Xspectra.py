from flask import Flask, render_template, request, jsonify
from pages.im_page import IMPage
from pages.se_page import SEPage
from pages.sfs_page import SFSPage
from pages.db_page import DBPage
from pages.acdss_page import ACDSSPage
import configparser

app = Flask(__name__)

# Load the config file
config = configparser.ConfigParser()
config.read('config.ini')


# Load the database config file
db_config = configparser.ConfigParser()
db_config.read('db_config.ini')



im_page = IMPage(app)
se_page = SEPage(app)
sfs_page = SFSPage(app)
acdss_page = ACDSSPage(app)
db_page = DBPage(app,db_config)


# Define a mapping of actions to corresponding page methods
action_handlers = {
    
    'ACDSS': acdss_page.fetch_and_analyze_acdss_logs,
    'SE': se_page.fetch_and_analyze_se_logs,
    'SFS': sfs_page.fetch_and_analyze_sfs_logs,
    'IM': im_page.fetch_and_analyze_im_logs,
}


def get_selected_ips(primary_ip, secondary_ip, scenario):
    if scenario == 'Primary':
        return [primary_ip]
    elif scenario == 'Secondary':
        return [secondary_ip]
    elif scenario == 'HA Scenario':
        return [primary_ip, secondary_ip]
    else:
        return []


# =========================================================================================================================
# ROUTES
# =========================================================================================================================

@app.route('/')
def index():
    return render_template('xspectra.html')

@app.route('/Display_Stats', methods=['POST'])
def analyze():
    action = request.form['action']
    if action == 'Connect & Generate Results':
        print("printing DB Stats")
        return db_page.fetch_and_generate_report() 
    else:
        lab = request.form.get('labSelect')
        logs_path = request.form.get('LogsPath')
        username = request.form.get('username')
        password = request.form.get('password')
        
        scenario = request.form.get('Scenario')

        # Fetch the IPs from the config file based on the lab
        primary_ip = config.get(lab, 'primary_ip')
        secondary_ip = config.get(lab, 'secondary_ip')

        # Determine which IPs to fetch based on the selected scenario
        selected_ips = get_selected_ips(primary_ip, secondary_ip, scenario)

        print("lab", lab)
        print("logs_path", logs_path)
        print("username", username)
        print("password", password)
        print("action", action)
        print("scenario", scenario)
        print("selected_ips", selected_ips)

        # Use the action to determine the appropriate page method and execute it
        if action in action_handlers:
            handler_method = action_handlers[action]
            return handler_method(selected_ips, logs_path, username, password)
        else:
            # Handle the case when the action is not found (return a JSON response, for example)
            return jsonify({'error': 'Invalid action'})


if __name__ == '__main__':
    app.run(debug=True, port=1000)
