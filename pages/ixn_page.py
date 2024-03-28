import logging
from flask import Flask, render_template, request, send_file
from .base_page import BasePage
from pages.sfs_page import SFSPage
from pages.se_page import SEPage
from pages.im_page import IMPage

class IXNPage(BasePage):

    def __init__(self, app):
        self.app = app
        self.sfs_page = SFSPage(app)  # Create an instance of SFSPage
        self.se_page = SEPage(app)  # Create an instance of SEPage
        self.im_page = IMPage(app)  # Create an instance of IMPage

        # Add logging configuration
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)

    def analyze(self):
        return render_template('ixndetails.html')

    def displayDetails(self):
        try:
            # Get IXN ID and uploaded log files
            ixn_id, sfs_file, im_file, se_file, acdss_file = self.get_uploaded_files_and_ixn_id()

            # Process each log file
            sfs_loglines = self.process_log_file(sfs_file)
            im_loglines = self.process_log_file(im_file)
            se_loglines = self.process_log_file(se_file)
            acdss_loglines = self.process_log_file(acdss_file)

            # Handle missing log files
            if not all([sfs_loglines]):
                self.logger.error("SFS log file is missing or empty")

            # Handle other log files if needed
            if not all([im_loglines, se_loglines, acdss_loglines]):
                self.logger.warning("One or more log files are missing or empty")

            sfs_summary_data, sfs_detailed_summary = self.sfs_page.generate_ixn_stats(sfs_loglines, ixn_id)
            se_vector_stats, se_total_vectors = self.se_page.generate_ixn_stats(se_loglines, ixn_id)
            im_summary = self.im_page.generate_ixn_stats(im_loglines, ixn_id)
            # Debugging: Print summary data
            # print("im_summary", im_summary)

            se_summary = {
                'vector_stats': se_vector_stats,
                'total_vectors': se_total_vectors
            }

            sfs_summary = {
               'summary_data':sfs_summary_data,
               'detailed_summary':sfs_detailed_summary,
            }
           

            return render_template('ixn_stats.html',
             ixn=ixn_id,
             sfs_summary=sfs_summary,
             se_summary= se_summary,
             im_summary = im_summary
             )


            # return render_template(
            #     'im_stats.html',
            #     im_ams_event_details=im_summary['im_ams_event_details'],
            #     im_ams_processing_details=im_summary['im_ams_processing_details'],
            #     im_sfs_summary_data=im_summary['im_sfs_summary_data']
            #         )




            # Perform further operations as needed
            # For example, you can pass these log lines to a template and render it
            # return render_template('display_ixn_details.html', ixn_id=ixn_id, sfs_loglines=sfs_loglines,
            #                        im_loglines=im_loglines, se_loglines=se_loglines, acdss_loglines=acdss_loglines)
        except Exception as e:
            self.logger.exception("An error occurred while displaying IXN details")
            return render_template('error.html',
                                   message="An error occurred while displaying IXN details. Please try again later.")

    def get_uploaded_files_and_ixn_id(self):
        # Retrieve IXN ID from the request
        ixn_id = request.form['ixn_id']

        # Retrieve uploaded log files
        sfs_file = request.files.get('sfs_file')  # Use get method to handle missing file gracefully
        im_file = request.files.get('im_file')    # Use get method to handle missing file gracefully
        se_file = request.files.get('se_file')    # Use get method to handle missing file gracefully
        acdss_file = request.files.get('acdss_file')  # Use get method to handle missing file gracefully

        # Return the IXN ID and uploaded log files
        return ixn_id, sfs_file, im_file, se_file, acdss_file

    def process_log_file(self, file):
        loglines = []
        if file:
            try:
                # Decode bytes to string
                for line in file.readlines():
                    try:
                        decoded_line = line.decode('utf-8')
                    except UnicodeDecodeError as e:
                        # Get the index of the problematic byte
                        error_index = e.args[2]
                        # Replace the problematic byte with None
                        decode_line = line[:error_index] + b'' + line[error_index + 1:]
                        decoded_line = decode_line.decode('utf-8')
                    loglines.append(decoded_line)  
                    
            except Exception as e:
                # Handle other exceptions gracefully
                print("Error processing file:", e)
                
        return loglines
