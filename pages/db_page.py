from flask import Flask, render_template, request
from .base_page import BasePage
import configparser
import psycopg2



class DBPage(BasePage):

    def __init__(self, app, db_config=None):
        self.app = app
        self.db_config = db_config

    def analyze(self):
        return render_template('db.html')

    def fetch_and_generate_report(self):
        db_details = self.fetch_db_details()

        if db_details:
            start_date = db_details.get('start_date')
            end_date = db_details.get('end_date')
            start_time = db_details.get('start_time')
            end_time = db_details.get('end_time')

            sql_queries, columns = self.fetch_sql_queries(start_date, end_date, start_time, end_time)


            if sql_queries:
                connection_status, results_list = self.connect_and_fetch_results(**db_details, sql_queries=sql_queries)

                # print(f"Connection Status: {connection_status}")
                # print(f"Results List: {results_list}")

                if connection_status:
                    return render_template('db_stats.html', results_list=results_list, columns=columns)
                else:
                    return render_template('error.html', message="Failed to establish a connection to the database.")
            else:
                return render_template('error.html', message="No SQL queries found.")
        else:
            return render_template('error.html', message="Unable to fetch database details.")

    def connect_and_fetch_results(self, db_ip, db_port, db_username, db_password, db_name, sql_queries, start_date, end_date, start_time, end_time):
        try:
            with psycopg2.connect(
                host=db_ip,
                port=db_port,
                user=db_username,
                password=db_password,
                database=db_name
            ) as conn:
                conn.autocommit = True

                with conn.cursor() as cursor:
                    cursor.execute(f"SET search_path TO afiniti")

                    results_list = []
                    for query in sql_queries:
                        # Execute query with parameterized placeholders
                        formatted_query = query % (f"'{start_date} {start_time}'", f"'{end_date} {end_time}'")
                        cursor.execute(formatted_query)
                        results = cursor.fetchall()
                        results_list.append({'raw_query': query, 'formatted_query': formatted_query, 'data': results})



            return True, results_list

        except psycopg2.Error as e:
            print(f"Database Error: {e}")
            return False, None


    def fetch_db_details(self):
        if request.method == 'POST' and 'action' in request.form and request.form['action'] == "Connect & Generate Results":

            lab = request.form.get('labSelect')
            start_date = request.form.get('start_date')
            start_time = request.form.get('start_time')
            end_date = request.form.get('end_date')
            end_time = request.form.get('end_time')

            # Fetch lab details from the separate database config file
            db_ip = self.db_config.get(lab, 'DB_IP')
            db_port = self.db_config.get(lab, 'DB_PORT')
            db_username = self.db_config.get(lab, 'DB_USERNAME')
            db_password = self.db_config.get(lab, 'DB_PASSWORD')
            db_name = self.db_config.get(lab, 'DB_DATABASE')

            # print(f"Database Details: {db_ip}, {db_port}, {db_username}, {db_password}, {db_name}")
            # print(f"Date and Time Details: Start Date: {start_date}, End Date: {end_date}, Start Time: {start_time}, End Time: {end_time}")

            return {
                'db_ip': db_ip,
                'db_port': db_port,
                'db_username': db_username,
                'db_password': db_password,
                'db_name': db_name,
                'start_date': start_date,
                'end_date': end_date,
                'start_time': start_time,
                'end_time': end_time
            }
        elif request.method == 'POST' :
            
            db_ip = request.form.get('db_ip')
            db_port = request.form.get('db_port')
            db_username = request.form.get('db_username')
            db_password = request.form.get('db_password')
            db_name = request.form.get('db_name')
            start_date = request.form.get('start_date')  # Change this line to get the start date
            end_date = request.form.get('end_date')  # Add this line to get the end date
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')

            # print(f"Database Details: {db_ip}, {db_port}, {db_username}, {db_password}, {db_name}")
            # print(f"Date and Time Details: Start Date: {start_date}, End Date: {end_date}, Start Time: {start_time}, End Time: {end_time}")

            return {
                'db_ip': db_ip,
                'db_port': db_port,
                'db_username': db_username,
                'db_password': db_password,
                'db_name': db_name,
                'start_date': start_date,
                'end_date': end_date,
                'start_time': start_time,
                'end_time': end_time
            }
   
        else:
            return None


    def fetch_sql_queries(self, start_date, end_date, start_time, end_time):
        queries = [
                "select distinct tenant , tenant_id  from t_acdr WHERE call_time >= %s AND call_time <= %s LIMIT 2;",
                "SELECT guid, tenant, tenant_id, ixn_id FROM t_acdr WHERE call_time >= %s AND call_time <= %s LIMIT 2;",
                """SELECT TO_CHAR(call_time, 'YYYY-MM-DD HH24') AS hour1,
                    COUNT(ixn_id) AS "# of calls",
                    AVG(EXTRACT(EPOCH FROM (data_creation_time - terminated_time))) AS AVG_ACDSS_DELAY_SEC,
                    MAX(EXTRACT(EPOCH FROM (data_creation_time - terminated_time))) AS MAX_ACDSS_DELAY_SEC,
                    MIN(EXTRACT(EPOCH FROM (data_creation_time - terminated_time))) AS MIN_ACDSS_DELAY_SEC,
                    AVG(EXTRACT(EPOCH FROM (db_insertion_time - data_creation_time))) AS AVG_ASYNC_DELAY_SEC,
                    MAX(EXTRACT(EPOCH FROM (db_insertion_time - data_creation_time))) AS MAX_ASYNC_DELAY_SEC,
                    MIN(EXTRACT(EPOCH FROM (db_insertion_time - data_creation_time))) AS MIN_ASYNC_DELAY_SEC
                    FROM afiniti.t_acdr
                    WHERE call_time >= %s AND call_time <= %s
                    GROUP BY hour1
                    ORDER BY hour1 LIMIT 2""",
                "select count(*) as AG_LOG_COUNT from t_aglog ta WHERE event_time >= %s AND event_time <= %s;",
                "select count(*) as CALL_QUEUE_LOG_COUNT from t_call_queue_log tcql WHERE event_time >= %s AND event_time <= %s;",
                "select count(*) as ACDR_COUNT from t_acdr ta WHERE call_time >= %s AND call_time <= %s;",
                "select count(distinct agent_id) DISTINCT_AGENT_COUNT from t_aglog ta WHERE event_time >= %s AND event_time <= %s;",
                """select agent_state, count(*) agent_state_count from t_aglog ta 
                    WHERE event_time >= %s AND event_time <= %s
                    GROUP BY agent_state
                    ORDER BY agent_state""",
                """select event_type, count(*) event_type_count from t_call_queue_log tcql 
                    WHERE event_time >= %s AND event_time <= %s
                    GROUP BY event_type
                    ORDER BY event_type"""
            ]

        columns = [
                ['Tenant', 'Tenant ID'],
                ['GUID', 'Tenant', 'Tenant ID', 'IXN ID'],
                ['hour1', '# of calls', 'AVG_ACDSS_DELAY_SEC', 'MAX_ACDSS_DELAY_SEC', 'MIN_ACDSS_DELAY_SEC', 'AVG_ASYNC_DELAY_SEC', 'MAX_ASYNC_DELAY_SEC', 'MIN_ASYNC_DELAY_SEC'],
                ['AG_LOG_COUNT'],  # AG LOG COUNT
                ['CALL_QUEUE_LOG_COUNT'],  # CALL QUEUE LOG COUNT
                ['ACDR_COUNT'],  # CDR COUNT
                ['DISTINCT_AGENT_COUNT'],  # TOTAL AGENT COUNT
                ['agent_state', 'agent_state_count'],  # AGENT STATE WISE COUNT_DB
                ['event_type', 'event_type_count']  # INTERACTION EVENT TYPE WISE COUNT_DB
            ]

        return queries, columns
