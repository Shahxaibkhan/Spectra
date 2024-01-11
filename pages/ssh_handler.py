import paramiko
import subprocess

class SSHHandler:
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        self.ssh = None

    def connect(self):
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(self.host, username=self.username, password=self.password)
            return True
        except Exception as e:
            print(f"Error connecting to {self.host}: {e}")
            return False

    def execute_command(self, command, universal_newlines=False):
        if self.ssh is not None:
            stdin, stdout, stderr = self.ssh.exec_command(command)
            return stdout.read().decode('utf-8')
        else:
            print("SSH connection not established.")
            return None

    def close(self):
        if self.ssh is not None:
            self.ssh.close()


def fetch_log_files(host, username, password, log_path):
    ssh_handler = SSHHandler(host, username, password)
    if ssh_handler.connect():
        command = f"cd {log_path} && ls *.log"
        log_file_names = ssh_handler.execute_command(command, universal_newlines=True).split('\n')[:-1]  # Exclude the last empty string
        log_files_content = []

        for file_name in sorted(log_file_names):
            file_path = f"{log_path}/{file_name}"
            command = f"cat {file_path}"  # Use 'cat' or an appropriate command for your file content retrieval
            file_content = ssh_handler.execute_command(command, universal_newlines=True)
            log_files_content.append(file_content)

        ssh_handler.close()

        # Merge log content into a single list
        merged_log_content = '\n'.join(log_files_content)
        return [merged_log_content]
    else:
        return None

