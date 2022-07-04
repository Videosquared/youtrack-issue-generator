import calendar
import requests
import sys
import json
import smtplib
import ssl
import datetime


def main():
    issue_generator = IssueGenerator()
    issue_generator.send_get("admin/projects?fields=id,name,shortName")


class IssueGenerator:

    def __init__(self):
        self.debug = False
        self.projects = self.get_projects()
        self.config_json = self.read_json("config.json")
        self.issues_json = self.read_json("issues.json")
        self.session = self.get_session()
        self.logs = []

    def generate(self):
        for issue in self.issues_json:
            if issue["project"] != "TEMPLATE" and self.check_date(issue):
                pass


    def create_issue(self):
        pass

    def set_custom_fields(self):
        pass

    # https://realpython.com/python-send-email/
    def mail_logs(self):
        pass

    def send_get(self, url):
        response = self.session.get(self.config_json["youtrack-api-url"] + url)

        if response.status_code == 200:
            return json.loads(response.content)
        else:
            # Log shit
            return 1

    def get_session(self):
        session = requests.Session()

        base_headers = {
            "Accept": "application/json",
            "Authorization": "Bearer " + self.config_json["youtrack-token"],
            "Content-Type": "application/json"
        }

        session.headers.update(base_headers)
        return session

    def get_projects(self):
        json_response = self.send_get("admin/projects?fields=id,name,shortName")

        if json_response == 1:
            self.mail_logs()
            print("ERROR: Unable to retrieve list of projects.")
            exit(1)

        projects = {}
        for project in json_response:
            projects[project["shortName"]] = project["id"]

        return projects

    @staticmethod
    def check_date(issue):
        patch_tuesday = IssueGenerator.find_patch_tuesday()
        today_day = datetime.date.today().day

        if issue["date"] == "patch-tuesday":
            if patch_tuesday == today_day:
                return True
            else:
                return False
        elif issue["date"] == "saturday-after-patch-tuesday":
            # Saturday After patch tuesday
            if patch_tuesday + 4 == today_day:
                return True
            else:
                return False

    @staticmethod
    def read_json(json_file):
        with open(json_file, "r") as file:
            content = file.read()
            json_data = json.loads(content)
        return json_data

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
        print(patch_tuesday)
        return patch_tuesday


# https://realpython.com/python-send-email/
if __name__ == "__main__":
    main()
