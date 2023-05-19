import argparse
import calendar
import configparser
import datetime
import glob
import json
import logging
import os.path
import re
import smtplib
import ssl
from logging.handlers import RotatingFileHandler

import requests
import yaml


def main():
    parser = argparse.ArgumentParser(description="YouTrack issue generator.")
    parser.add_argument("--debug", help="Enable debug mode.", action="store_true")
    parser.add_argument("-t", "--configtest", help="Configuration test.", action="store_true")
    parser.add_argument("--dryrun", help="Complete a dry run with logs", action="store_true")
    args = parser.parse_args()

    log_lvl = logging.DEBUG if args.debug else logging.INFO

    configure_logger(log_lvl)

    logging.getLogger().info("Starting...")
    generator = IssueGenerator(args.debug, args.configtest)
    generator.get_projects()
    generator.get_issues()
    generator.run()
    generator.mail_logs()


def configure_logger(log_level):
    # log_filename = "generator.log"
    log_filename = os.path.dirname(os.path.realpath(__file__)) + "/logs/generator.log"

    log_format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%d-%m-%Y %H:%M:%S")

    logging.basicConfig(level=log_level,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%d-%m-%Y %H:%M:%S")
    logger = logging.getLogger()
    existing_log_file = os.path.isfile(log_filename)
    file_handler = RotatingFileHandler(log_filename, backupCount=7)
    if existing_log_file:
        file_handler.doRollover()
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)


class IssueGenerator:
    def __init__(self, debug, config_test):
        self.logger = logging.getLogger()
        self.debug = debug
        self.config_test = config_test
        self.cwd = os.path.dirname(os.path.realpath(__file__))

        self.logger.info("Reading configuration file.")
        self.config = configparser.ConfigParser()
        self.config.read_file(open(self.cwd + "/" + "config.ini", "r"))

        self.issues = []
        self.session = self.get_session()
        self.projects = {}

        self.created_issues = []
        self.skipped_issues = []
        self.error_issues = []

    def run(self):
        if len(self.issues) == 0:
            self.logger.warning("No issues have been found to generate.")
            return

        for issue in self.issues:
            if self.check_date(issue):
                if issue.get("project") in self.projects.keys():
                    self.logger.info(f"""Generating {issue.get("project")} - {issue.get("summary")}""")
                    data = self.create_issue(issue)
                    response = self.send_post("api/issues", data)
                    if response.status_code == 200:
                        self.created_issues.append(issue)
                        self.logger.info(f"""Created {issue.get("project")} - {issue.get("summary")}: SUCCESS""")
                    else:
                        self.error_issues.append(issue)
                        self.logger.error(f"""Cannot create issue {issue.get("summary")} in project {issue.get("project")}. Ensure all field names are valid and correct.""")
                else:
                    self.logger.error(f"""Project {issue.get("project")} is not found.""")
            else:
                self.skipped_issues.append(issue)
                self.logger.info(f"""Issue {issue.get("project")} - {issue.get("summary")}: SKIPPED""")

    def create_issue(self, issue):
        data = {
            "project": {
                "id": self.projects.get(issue.get("project"))
            },
            "summary": issue.get("summary"),
            "description": issue.get("description")
        }

        if "custom-fields" in issue.keys() and len(issue.get("custom-fields").keys()) > 0:
            self.logger.info("Retrieving custom field information.")
            remote_cust_fields = self.get_custom_fields(issue.get("project"))

            if remote_cust_fields is not None:
                data.update({"customFields": []})
                for field_name in issue.get("custom-fields").keys():
                    for field in remote_cust_fields:
                        if field_name == field.get("name"):
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
                            break

        self.logger.info("Add custom field data: SUCCESS")
        return data


    def send_post(self, url, data):
        self.logger.debug(f"""Sending HTTP POST request to: {self.config.get("youtrack", "url") + url} with {data}""")
        return self.session.post(self.config.get("youtrack", "url") + url, json=data)

    def send_get(self, url):
        self.logger.debug(f"""Sending GET request to {self.config.get("youtrack", "url") + url}""")

        response = self.session.get(self.config.get("youtrack", "url") + url)
        if response.status_code == 200:
            self.logger.debug(f"{response.json()}")
            return json.loads(response.content)
        else:
            self.logger.warning("Non HTTP.200 response code received.")
            return None

    def get_issues(self):
        self.logger.info("Reading issues directory.")
        issue_root = self.cwd + "/issues"
        issues = glob.glob("**/*.yaml", root_dir=issue_root, recursive=True)
        for issue_file in issues:
            path = issue_root + "/" + issue_file
            with open(path, "r") as file:
                self.issues.append(yaml.safe_load(file))

        self.logger.info(f"Found {len(issues)} issues.")


    def get_projects(self):
        self.logger.info("Getting project data from YouTrack...")
        response = self.send_get("api/admin/projects?fields=id,name,shortName")
        if response is None:
            self.logger.critical("Unable to retrieve projects from YouTrack, ensure credentials are correct and this "
                                 "machine is able to communicate with your YouTrack instance.")
            return

        for proj in response:
            self.projects[proj["shortName"]] = proj["id"]

        self.logger.info("Retrieve project data: SUCCESS")

    def get_session(self):

        session = requests.Session()
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer " + self.config.get("youtrack", "token"),
            "Content-Type": "application/json"
        }

        session.headers.update(headers)
        return session

    def get_custom_fields(self, project):
        url = "api/issues?fields=idReadable,id,project%28id,name%29,summary" \
              ",description,customFields%28name,$type,value%28name,login%29%29&query=in:{}&$top=1".format(project)

        json_response = self.send_get(url)

        # Check if the response from YouTrack API is not valid.
        if json_response == 1:
            self.logger.warning("Invalid HTTP response received.")
            return None

        return json_response[0]["customFields"]

    def mail_logs(self):
        log_file = open(self.cwd + "/" + "latest-logs.log", "r")

        # Create the email contents in the format of:
        # Subject: <subject>
        # From: from@example.com
        # To: to@example.com
        #
        # <content>

        message = "Subject: YouTrack Issue Generator Report {}\nFrom: {}\nTo: {}\n\n" \
            .format(datetime.datetime.now().strftime("%d-%m-%Y"), self.config.get("smtp", "sender-email"),
                    self.config.get("smtp", "recipient-email"))

        message = message + "##### YouTrack Issue Generator Summary #####\n\n"

        if len(self.created_issues) == 0 and len(self.skipped_issues) ==0 and len(self.error_issues) == 0:
            message = message + f"""No issues have been detected.\n"""
        else:
            if len(self.created_issues) > 0:
                for issue in self.created_issues:
                    message = message + f"""CREATED: {issue.get("project")} - {issue.get("summary")}\n"""

            if len(self.skipped_issues) > 0:
                for issue in self.skipped_issues:
                    message = message + f"""SKIPPED: {issue.get("project")} - {issue.get("summary")}\n"""

            if len(self.error_issues) > 0:
                for issue in self.error_issues:
                    message = message + f"""ERROR: {issue.get("project")} - {issue.get("summary")}\n"""

        message = message + "\n"

        with open(self.cwd + "/logs/generator.log", "r") as log_file:
            message = message + log_file.read()

        # Creating an SSL connection to the SMTP server and sending the email.
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(self.config.get("smtp", "server"), int(self.config.get("smtp", "port")),
                              context=context) as smtp_server:
            smtp_server.login(self.config.get("smtp", "username"), self.config.get("smtp", "password"))
            smtp_server.sendmail(self.config.get("smtp", "sender-email"), self.config.get("smtp", "recipient-email"),
                                 message)

        log_file.close()

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


if __name__ == "__main__":
    main()
