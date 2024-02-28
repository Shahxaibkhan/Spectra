# acdss_page.py
import io, os, zipfile, re
from .base_page import BasePage
from pages.ssh_handler import fetch_log_files
from flask import Flask, render_template, request, send_file
import json



class ACDSSPage(BasePage):

    AGENT_STATES = {
        -1: 'UNKNOWN',
        0: 'LOGGEDOUT',
        1: 'LOGGEDIN',
        2: 'IDLE',
        3: 'ONBREAK',
        4: 'ASSIGNED',
        5: 'TALKING',
        6: 'WRAP',
        7: 'RESERVED',
        15: 'AGENT_AVAIL',
        16: 'ASL_EVENT',
        17: 'RR_RESOURCE_BUSY',
        18: 'NETWORK_OUT_OF_SERVICE'
    }

    def __init__(self, app):
        self.app = app

    def analyze(self):
        # Implement IM analysis logic here
        return render_template('acdss.html')

    def generate_stats(self):
        log_file = self.file_upload_and_processing_logs()
        return self.generate_acdss_stats(log_file)

    def generate_acdss_stats(self, log_file):
        call_state_sorted_logs = self.extract_and_sort_call_event_logs(log_file)
        call_events_count, ixn_id_states = self.generate_call_events_reports(call_state_sorted_logs)

        agent_state_sorted_logs = self.extract_and_sort_agent_state_logs(log_file)
        agent_state_count_named, agent_details = self.generate_agent_reports(agent_state_sorted_logs)

        tenant_report,agent_group_report, agent_details_report = self.extract_and_generate_reports(log_file)

        # Use 'call_events_count', 'ixn_id_states', 'agent_state_count_named', 'agent_details',
        # 'unique_agent_ids_count', 'tenant_report', 'agent_group_count', 'agent_group_report', 'agent_details_report'
        # as needed in your HTML template or further processing
        # print("agent_group_count: ",agent_group_count)
        return render_template(
            'acdss_stats.html',
            call_events_count=call_events_count,
            ixn_id_states=ixn_id_states,
            Agent_states_count=agent_state_count_named,
            Agent_id_states=agent_details,
            Tenant_Report=tenant_report,
            Agent_Group_Report=agent_group_report,
            Agent_Details_Report=agent_details_report
        )
    

    def file_upload_and_processing_logs(self):
        log_file = request.files['log_file']

        # Get the current working directory
        current_dir = os.getcwd()

        # Specify the directory for saving and reading files
        upload_dir = os.path.join(current_dir, 'logs_uploaded_files')
        
        # Ensure the directory exists
        os.makedirs(upload_dir, exist_ok=True)

        # Save uploaded files with absolute paths
        log_file_path = os.path.join(upload_dir, 'logfile.log')
        log_file.save(log_file_path)

        with open(log_file_path, 'r') as log_file:
            log_file =log_file.readlines()

        return log_file

    def extract_and_sort_call_event_logs(self, logs):
        extracted_logs = []
        for log_line in logs:
            match = re.search(r'call_event:(\d+)\|\[1\]ixn_id:(\d+)\|.*data_timestamp:(\d+)\|aicore_tm:(\d+)', log_line)
            if match:
                call_event = int(match.group(1))
                ixn_id = int(match.group(2))
                data_timestamp = int(match.group(3))
                aicore_tm = int(match.group(4))
                extracted_logs.append({
                    'call_event': call_event,
                    'ixn_id': ixn_id,
                    'data_timestamp': data_timestamp,
                    'aicore_tm': aicore_tm,
                })

        # Sort the logs based on ixn_id
        sorted_logs = sorted(extracted_logs, key=lambda x: x['ixn_id'])
        return sorted_logs

    def generate_call_events_reports(self, sorted_logs):
        call_events_count = {}
        ixn_id_states = {}

        for log in sorted_logs:
            ixn_id = log['ixn_id']
            call_event = log['call_event']

           # Update count for each call event
            call_events_count[call_event] = call_events_count.get(call_event, 0) + 1

            # Update detailed event table
            ixn_id_states.setdefault(ixn_id, []).append({
                'call_event': call_event,
                'data_timestamp': log['data_timestamp'],
                'aicore_tm': log['aicore_tm'],
            })

         # Create call_events_count_named dynamically without specifying desired_order
        call_events_count_named = {i: {'event_number': i, 'event_name': self.get_event_name(i), 'count': count} for i, count in sorted(call_events_count.items())}

        return call_events_count_named, ixn_id_states

    def extract_and_sort_agent_state_logs(self, logs):
        extracted_logs = []
        
        for log_line in logs:
            if 'INFO:' in log_line:
                match = re.search(r'state:(\d+).*agent_id:(\d+).*data_timestamp:(\d+).*aicore_tm:(\d+)', log_line)
                if match:
                    agent_state = int(match.group(1))
                    agent_id = int(match.group(2))
                    data_timestamp = int(match.group(3))
                    aicore_tm = int(match.group(4))
                    extracted_logs.append({
                    'agent_state': agent_state,
                    'agent_id': agent_id,
                    'data_timestamp': data_timestamp,
                    'aicore_tm': aicore_tm,
                })

        # Sort the logs based on ixn_id
        sorted_logs = sorted(extracted_logs, key=lambda x: x['agent_id'])
        return sorted_logs


    def generate_agent_reports(self, sorted_logs):
        agent_state_count = {}
        agent_details = {}
        

        for log in sorted_logs:
            agent_id = log['agent_id']
            agent_state = log['agent_state']

            # Update count for each agent state
            agent_state_count[agent_state] = agent_state_count.get(agent_state, 0) + 1

          
            # Update detailed agent table for each occurrence of agent_id
            agent_details.setdefault(agent_id, []).append({
                'agent_state': agent_state,
                'data_timestamp': log['data_timestamp'],
                'aicore_tm': log['aicore_tm'],
            })

            

        # Convert agent_state_count to named dictionary
        agent_state_count_named = {i: {'agent_state': i, 'state_enum': self.get_agent_state_enum(i), 'count': count}
                                for i, count in sorted(agent_state_count.items())}

        return agent_state_count_named, agent_details

    def extract_and_generate_reports(self, logs):
        agent_info = {}
        agent_group_info = {}

        for log_line in logs:
           if 'INFO:' in log_line:
                match = re.search(r'ixn id : (\d+).*event_type: (\d+).*Tenant ID: (\d+).*channel: (\d+).*agent_id: (\d+).*calltype_id : (\d+).*direction : (-?\d+).*agentGroupID : (\d+)', log_line)
                if match:
                    ixn_id = int(match.group(1))
                    event_type = int(match.group(2))
                    tenant_id = int(match.group(3))
                    channel = int(match.group(4))
                    agent_id = int(match.group(5))
                    calltype_id = int(match.group(6))
                    direction = int(match.group(7))
                    agent_group_id = int(match.group(8))

                    # Update agent_info dictionary
                    agent_info.setdefault((agent_id, tenant_id), {'tenant_id': tenant_id, 'agent_group_id': agent_group_id,
                                                'event_type': event_type, 'direction': direction, 'calltype_id': calltype_id,
                                                'channel': channel, 'agent_id': agent_id, 'ixn_id': ixn_id})

                    # Update agent_group_info dictionary
                    # Update agent_group_info dictionary
                    agent_group_info.setdefault(agent_group_id, set()).add((agent_id, tenant_id))

        # Generate reports
        tenant_report = self.generate_tenant_report(agent_info)
        agent_group_report = self.generate_agent_group_report(agent_group_info)
        agent_details_report = self.generate_agent_details_report(agent_info)

        return tenant_report, agent_group_report, agent_details_report


    def generate_tenant_report(self, agent_info):
        tenant_count = {}
        for agent_id, info in agent_info.items():
            tenant_id = info['tenant_id']
            tenant_count[tenant_id] = tenant_count.get(tenant_id, 0) + 1

        tenant_report = [{'TenantID': tenant_id, 'TotalAgents': count} for tenant_id, count in tenant_count.items()]
        return tenant_report

    def generate_agent_group_report(self, agent_group_info):
        agent_group_report = [{'AgentGroup': group_id, 'TotalAgents': len(agent_ids)} for group_id, agent_ids in agent_group_info.items()]
        return agent_group_report

    def generate_agent_details_report(self, agent_info):
        agent_details_report = [{'agent_id': agent_id, 'TenantID': info['tenant_id'],'EventType': info['event_type'],
                                 'AgentGroupID': info['agent_group_id'], 'ixn_id': info['ixn_id'],
                                 'Direction': info['direction'], 'CallTypeID': info['calltype_id'],
                                 'Channel': info['channel']} for agent_id, info in agent_info.items()]
        return agent_details_report



    def get_agent_state_enum(self, agent_state):
        return self.AGENT_STATES.get(agent_state, 'Others')

    def get_event_name(self, event_number):
        event_names = {
            0: 'UNKNOWN', 1: 'OFFERED', 2: 'ROUTE_REQUESTED', 3: 'ROUTE_SELECTED',
            4: 'ROUTE_TIMEOUT', 5: 'RINGING', 6: 'CONNECTED', 7: 'DISCONNECTED',
            8: 'TERMINATED', 9: 'HELD', 10: 'RESUMED', 11: 'ROUTE_ENDED', 12: 'TRANSFERRED',
            20: 'DE_QUEUED', 21: 'CONFERENCED', 22: 'RONA'
        }
        return event_names.get(event_number, 'Others')

   