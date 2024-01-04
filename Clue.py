from flask import Flask, render_template, request, send_file
import os
import io
import re
import tempfile
from datetime import datetime

app = Flask(__name__)

UPLOAD_FOLDER = tempfile.mkdtemp()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('clue.html')

def process_logs(log_files, log_level):
    unified_logs = []
    log_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{6})\s+(\d+)\s+(\S+)\s*:\s*(.*)')

    for log_file in log_files:
        with open(log_file, 'r') as f:
            for line in f:
                match = log_pattern.match(line)
                if match:
                    timestamp = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S,%f')
                    level = match.group(3)
                    message = match.group(4)

                    if log_level == 'ALL' or log_level == level:
                        unified_logs.append((timestamp, level, message))

    unified_logs.sort(key=lambda x: x[0])
    return unified_logs

@app.route('/upload-log', methods=['POST'])
def upload_log():
    log_files = []
    log_level = request.form.get('log_level')

    for file in request.files.getlist('log_file[]'):
        if file.filename != '':
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)
            log_files.append(file_path)

    unified_logs = process_logs(log_files, log_level)

    output_log = io.BytesIO()

    for log in unified_logs:
        output_log.write(f"{log[0]} [{log[1]}] {log[2]}\n".encode())

    output_log.seek(0)
    return send_file(output_log, as_attachment=True, download_name='unified_logs.log')

if __name__ == '__main__':
    app.run(debug=True, port=8000)
