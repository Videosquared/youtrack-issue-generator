import calendar
import requests
import json
import smtplib
import ssl
import datetime
import re
import sys
import os


# The main class responsible for the main calculations and the generation of issues.
class IssueGenerator:

    def __init__(self):
        file_path = os.path.dirname(os.path.realpath(__file__))

        self.logger = Logger(file_path)
        self.emailer = Emailer(self.logger)
        self.config_json = self.read_json(file_path + "/" + "config.json", self.logger, self.emailer)
        self.issues_json = self.read_json(file_path + "/" + "issues.json", self.logger, self.emailer)
        self.session = self.get_session()
        self.projects = self.get_projects()

    # This is the main method that orchestrates the generation of issues. It first
    # checks if it's not a template issue and the date is satisfied. It proceeds to check
    # the requested project is available. If so, it proceeds to create the data (json) required for
    # creation of the issue. When creating an issue, if the response code from the POST request
    # is not 200, it means an error has occurred and the issue is not created.
    def run(self):
        for issue in self.issues_json:
            # Check if it's not a template issue and the date is satisfied.
            if issue["project"] != "TEMPLATE-PROJECT" and self.check_date(issue):
                # Check if the project can be accessed and have an ID. Else skip this issue.
                if issue["project"] in self.projects.keys():
                    self.logger.log("INFO", "Creating issue {} {}...".format(issue["project"], issue["summary"]))
                    data = self.create_issue(issue)
                    response = self.send_post("api/issues", data)

                    # Check the response code from creating the issue. If its not 200
                    # it means it has failed.
                    if response.status_code == 200:
                        self.logger.log_created_issue(issue)
                    else:
                        self.logger.log_error_issue(issue, "Ensure the fields are correct (including custom field "
                                                           "names and values) for this issue/project are correct.")

                else:
                    self.logger.log_error_issue(issue, "The project provided for the issue is not valid. Please ensure "
                                                       "the user has access to the project and that the "
                                                       "project name is correct.")
            else:
                self.logger.log_skipped_issue(issue)

        # Clean up the log files and send the logs via email.
        self.logger.clean_up()
        self.emailer.mail_logs()

    # This will create the dictionary (json) required for creating the issue. It starts
    # by creating the base components of an issue and then checks if there are custom
    # field(s) parameters set. If so, it will add the values for the custom field(s) into
    # the existing dictionary.
    def create_issue(self, issue):
        data = {}
        data.update({"project": {"id": self.projects.get(issue["project"])}})
        data.update({"summary": issue["summary"]})
        data.update({"description": issue["description"]})

        if "custom-fields" in issue.keys():
            self.logger.log("INFO", "Issue has custom field(s).")
            custom_fields_response = self.get_custom_fields(issue["project"])

            # This checks if the data (custom field(s) types) can be acquired from the YouTrack
            # instance. If not, the custom fields will be skipped and base issue will be generated.
            if custom_fields_response != 1:
                data.update({"customFields": []})
                for field_name in issue["custom-fields"].keys():
                    for field in custom_fields_response:
                        if field_name == field["name"]:
                            if field_name == "Assignee":
                                data.get("customFields").append({"name": field["name"],
                                                                 "$type": field["$type"],
                                                                 "value": {
                                                                     "login": issue["custom-fields"]["Assignee"]}})
                            else:
                                data.get("customFields").append({"name": field["name"],
                                                                 "$type": field["$type"],
                                                                 "value": {
                                                                     "name": issue["custom-fields"][field_name]}})
            else:
                self.logger.log("WARN", "Custom field(s) data cannot be acquired from the YouTrack instance. "
                                        "Base issue will be generated.")

        return data

    # This will send a GET request to the given URL. It will check if the response is valid (status code 200)
    # otherwise return 1 to indicate the response is invalid.
    def send_get(self, url):
        self.logger.log("INFO", "Sending GET request to {}".format(self.config_json["youtrack-api-url"] + url))
        response = self.session.get(self.config_json["youtrack-api-url"] + url)

        # Checking if the response is valid.
        if response.status_code == 200:
            return json.loads(response.content)
        else:
            self.logger.log("ERROR", "Invalid HTTP status code received from server. Check provided youtrack URL/token"
                                     " and this computer/server is able to access your YouTrack "
                                     "instance (firewalled?).")
            return 1

    # This will send a POST request to the given URL with the provided data.
    def send_post(self, url, data):
        self.logger.log("INFO", "Sending POST request to {} with {}".format(self.config_json["youtrack-api-url"] +
                                                                            url, data))
        return self.session.post(self.config_json["youtrack-api-url"] + url, json=data)

    # This will create a session object and set the default headers required for the YouTrack API.
    def get_session(self):
        session = requests.Session()

        # Headers required for the YouTrack API.
        base_headers = {
            "Accept": "application/json",
            "Authorization": "Bearer " + self.config_json["youtrack-token"],
            "Content-Type": "application/json"
        }

        session.headers.update(base_headers)
        return session

    # This will get a list of projects the token owner has access to from the YouTrack API and then create a
    # dictionary of "shortName" (as key) and "id" (as value).
    def get_projects(self):
        self.logger.log("INFO", "Getting project IDs...")
        json_response = self.send_get("api/admin/projects?fields=id,name,shortName")

        # Check if the response is valid. If not, we will exit the program as it cannot be continued if we are
        # unable to retrieve the project IDs.
        if json_response == 1:
            self.logger.log("ERROR", "Unable to retrieve list of projects from YouTrack instance. Ensure credentials "
                                     "are correct and this computer/server is able to talk to the YouTrack instance.")
            self.logger.clean_up()
            self.emailer.mail_logs()
            print("ERROR: Unable to retrieve list of projects.")
            exit(1)

        projects = {}
        for project in json_response:
            projects[project["shortName"]] = project["id"]

        return projects

    # This will get the custom fields for a given project. If we are unable to retrieve the custom field(s) data,
    # we will return 1.
    def get_custom_fields(self, project):
        url = "api/issues?fields=idReadable,id,project%28id,name%29,summary" \
              ",description,customFields%28name,$type,value%28name,login%29%29&query=in:{}&$top=1".format(project)

        self.logger.log("INFO", "Getting custom field(s) data...")
        json_response = self.send_get(url)

        # Check if the response from YouTrack API is not valid.
        if json_response == 1:
            self.logger.log("ERROR", "Unable to retrieve custom field(s) data. Will not set custom field(s) values.")
            return 1

        return json_response[0]["customFields"]

    # This will check the date field for the given issue. If the date set is "today" then it will return
    # True, otherwise False.
    @staticmethod
    def check_date(issue):
        patch_tuesday = IssueGenerator.find_patch_tuesday()
        day_of_week = datetime.date.today().weekday() + 1
        today = datetime.date.today()
        today_day = datetime.date.today().day
        today_month = datetime.date.today().month

        if issue["date"] == "daily":
            # Daily Tickets
            return True
        elif issue["date"] == "weekly" and issue["day-of-week"] == day_of_week:
            # Day of week (1 is Monday and 7 is Sunday)
            return True
        elif issue["date"] == "patch-tuesday" and patch_tuesday == today_day:
            # Day of patch tuesday (second tuesday of month)
            return True
        elif issue["date"] == "saturday-after-patch-tuesday" and patch_tuesday + 4 == today_day:
            # Saturday After patch tuesday
            return True
        elif type(issue["date"]) == int and today_day == issue["date"]:
            # Create monthly tickets
            return True
        elif bool(re.match(r"^([0-2][0-9]|(3)[0-1])(-)(((0)[0-9])|((1)[0-2]))(-)\d{4}$", issue["date"])) and \
                datetime.datetime.strptime(issue["date"], "%d-%m-%Y").date() == today:
            # This will create tickets on a specific day in the year specified
            return True
        elif bool(re.match(r"^([0-2][0-9]|(3)[0-1])(-)(((0)[0-9])|((1)[0-2]))$", issue["date"])) and \
                datetime.datetime.strptime(issue["date"], "%d-%m").date().day == today_day and \
                datetime.datetime.strptime(issue["date"], "%d-%m").date().month == today_month:
            # Create yearly tickets on the day and month specified
            return True
        else:
            return False

    # This will read the json file requested and if the file is not found, it will terminate the program as its
    # primarily used to read configuration files, and they are REQUiRED.
    @staticmethod
    def read_json(json_file, logger, emailer):

        # Attempt to read the file passed in.
        try:
            with open(json_file, "r") as file:
                content = file.read()
                json_data = json.loads(content)
                return json_data
        # If the file cannot be found we will log this and terminate the program.
        except FileNotFoundError:
            logger.log("INFO", "{} file not found.".format(json_file))
            logger.clean_up()
            emailer.mail_logs()
            print("ERROR: {} file not found.".format(json_file))
            exit(1)

    # This will find the day that patch tuesday (second Tuesday of the month) and return the day number.
    @staticmethod
    def find_patch_tuesday():
        # Init the variable, random value
        patch_tuesday = 12

        # Get the calendar for current month and year
        month_cal = calendar.monthcalendar(datetime.date.today().year, datetime.date.today().month)

        # For weeks 2 and 3, we check in order if the patch tuesday is
        for i in [1, 2]:
            week = month_cal[i]
            if week[calendar.TUESDAY] >= 8 <= 14:
                patch_tuesday = week[calendar.TUESDAY]
                break

        return patch_tuesday


# The class responsible for logging data during the creation of issues.
class Logger:

    def __init__(self, file_path):
        self.start_time = datetime.datetime.now().strftime("%H:%M:%S %d-%m-%Y")
        self.log_file = open(file_path + "/" + "latest-logs.log", "w")
        self.log_file.truncate()
        self.end_time = 0
        self.issues = []  # This contains a tuple of the issue and the result for that issue. i.e. (issue, "CREATED").

        self.log("INFO", "Starting YouTrack Issue Generator....")

    # This will write the generic log message in the format "time date [TYPE]: message".
    def log(self, log_type, log_string):
        self.log_file.write("{} [{}]: {}\n".format(datetime.datetime.now().strftime("%H:%M:%S %d-%m-%Y"), log_type,
                                                   log_string))

    # This will log that an issue has been skipped.
    def log_skipped_issue(self, issue):
        # Only log issues that are NOT template issues.
        if issue["project"] != "TEMPLATE-PROJECT":
            # Log format is "time date [SKIPPED ISSUE]: Project - Summary"
            self.log_file.write("{} [SKIPPED ISSUE]: {} - {}\n".format(datetime.datetime.now().
                                                                       strftime("%H:%M:%S %d-%m-%Y"), issue["project"],
                                                                       issue["summary"]))
            self.issues.append((issue, "SKIPPED"))

    # This will log that an issue has been successfully created on YouTrack.
    def log_created_issue(self, issue):
        # Log format is "time date [CREATED ISSUE]: Project - Summary"
        self.log_file.write(
            "{} [CREATED ISSUE]: {} - {}\n".format(datetime.datetime.now().strftime("%H:%M:%S %d-%m-%Y"),
                                                   issue["project"], issue["summary"]))
        self.issues.append((issue, "CREATED"))

    # This will log that an error has occurred when creating this issue.
    def log_error_issue(self, issue, msg):
        # Log format is "time date [SKIPPED ISSUE]: Project - Summary"
        self.log_file.write(
            "{} [ERROR ISSUE]: {} - {} [{}]\n".format(datetime.datetime.now().strftime("%H:%M:%S %d-%m-%Y"),
                                                      issue["project"], issue["summary"], msg))
        self.issues.append((issue, "ERROR"))

    # This is the final step, we write the final stop message and close the file.
    # We then open the file again for read and then prepend a summary to the start of the file.
    def clean_up(self):
        self.log("INFO", "Stopping YouTrack Issue Generator")
        self.log_file.close()

        # Open the file for read and write.
        self.log_file = open("latest-logs.log", "r+")
        logs = self.log_file.read()  # Read all the current logs.
        self.log_file.seek(0)  # Go to start of file.

        # Write the summary of the issues.
        self.log_file.write("##### YouTrack Issue Generator Summary #####\n\n")
        if len(self.issues) == 0:
            self.log_file.write("No issues were provided or an error occurred.\n")
        else:
            for item in self.issues:
                self.log_file.write("{}: {} - {}\n".format(item[1], item[0]["project"],
                                                           item[0]["summary"]))

        self.log_file.write("\nIssue generation started at:\n")
        self.log_file.write(self.start_time + "\n")

        self.log_file.write("Issue generation finished at:\n")
        self.log_file.write(datetime.datetime.now().strftime("%H:%M:%S %d-%m-%Y") + "\n\n")

        # Append logs after summary.
        self.log_file.write(logs)
        self.log_file.close()


# The class responsible for emailing the completed logs to the recipient.
class Emailer:

    def __init__(self, logger):
        self.config_json = IssueGenerator.read_json("config.json", logger, self)

    # This will open the read the log file, create an email message. Then create an SSL
    # connection to the SMTP server and send the email.
    def mail_logs(self):
        log_file = open("latest-logs.log", "r")

        # Create the email contents in the format of:
        # Subject: <subject>
        # From: from@example.com
        # To: to@example.com
        #
        # <content>

        message = "Subject: YouTrack Issue Generator Report {}\nFrom: {}\nTo: {}\n\n" \
            .format(datetime.datetime.now().strftime("%d-%m-%Y"), self.config_json["smtp-sender-email"],
                    self.config_json["smtp-receiver-email"])
        message = message + log_file.read()

        # Creating an SSL connection to the SMTP server and sending the email.
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(self.config_json["smtp-server"], self.config_json["smtp-server-port"],
                              context=context) as smtp_server:
            smtp_server.login(self.config_json["smtp-username"], self.config_json["smtp-password"])
            smtp_server.sendmail(self.config_json["smtp-sender-email"], self.config_json["smtp-receiver-email"],
                                 message)


# Allows the program to run by itself.
if __name__ == "__main__":
    issue_generator = IssueGenerator()
    issue_generator.run()
