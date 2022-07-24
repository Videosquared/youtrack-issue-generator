import calendar
import requests
import sys
import json
import smtplib
import ssl
import datetime
import re


# https://www.jetbrains.com/help/youtrack/devportal/api-howto-create-issue-with-fields.html#step-by-step
# https://www.nylas.com/blog/use-python-requests-module-rest-apis/
# https://requests.readthedocs.io/en/latest/user/advanced/


# https://stackoverflow.com/questions/62985961/how-to-use-requests-session-so-that-headers-are-presevred-and-reused-in-subseque

# https://support.hostinger.com/en/articles/1575756-how-to-get-email-account-configuration-details-for-hostinger-email
# https://realpython.com/python-send-email/


def main():
    issue_generator = IssueGenerator()
    issue_generator.run()


class IssueGenerator:

    def __init__(self):
        self.debug = False
        self.config_json = self.read_json("config.json")
        self.issues_json = self.read_json("issues.json")
        self.session = self.get_session()
        self.projects = self.get_projects()
        self.logger = Logger()

    def run(self):
        for issue in self.issues_json:
            if issue["project"] != "TEMPLATE-PROJECT" and self.check_date(issue):
                if issue["project"] in self.projects.keys():
                    data = self.create_issue(issue)
                    self.send_post("api/issues", data)
                else:
                    # log that the project iD is incorrect
                    pass

    def create_issue(self, issue):
        data = {}
        data.update({"project": {"id": self.projects.get(issue["project"])}})
        data.update({"summary": issue["summary"]})
        data.update({"description": issue["description"]})

        if "custom-fields" in issue.keys():
            data.update({"customFields": []})
            custom_fields_response = self.get_custom_fields(issue["project"])
            for field_name in issue["custom-fields"].keys():
                for field in custom_fields_response:
                    if field_name == field["name"]:
                        if field_name == "Assignee":
                            data.get("customFields").append({"name": field["name"],
                                                             "$type": field["$type"],
                                                             "value": {"login": issue["custom-fields"]["Assignee"]}})
                        else:
                            data.get("customFields").append({"name": field["name"],
                                                             "$type": field["$type"],
                                                             "value": {"name": issue["custom-fields"][field_name]}})

        return data

    def send_get(self, url):
        response = self.session.get(self.config_json["youtrack-api-url"] + url)
        # print(self.config_json["youtrack-api-url"] + url)
        # print(self.session.headers)
        # print(response.text)
        if response.status_code == 200:
            return json.loads(response.content)
        else:
            # Log shit
            return 1

    def send_post(self, url, data):
        response = self.session.post(self.config_json["youtrack-api-url"] + url, json=data)
        # log response

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
        json_response = self.send_get("api/admin/projects?fields=id,name,shortName")

        if json_response == 1:
            self.logger.clean_up()
            print("ERROR: Unable to retrieve list of projects.")
            exit(1)

        projects = {}
        for project in json_response:
            projects[project["shortName"]] = project["id"]

        return projects

    def get_custom_fields(self, project):
        url = "api/issues?fields=idReadable,id,project%28id,name%29,summary" \
              ",description,customFields%28name,$type,value%28name,login%29%29&query=in:{}&$top=1".format(project)

        # print(url)

        json_response = self.send_get(url)
        if json_response == 1:
            self.logger.clean_up()
            print("ERROR: Unable to retrieve list of projects.")
            exit(1)


        # print(json_response)
        return json_response[0]["customFields"]

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

        return patch_tuesday


class Logger:

    def __init__(self):
        self.start_time = datetime.datetime.now().strftime("%H:%M:%S %d-%m-%Y")
        self.log_file = open("latest-logs.log", "w")
        self.log_file.truncate()
        self.end_time = 0
        self.issues = []
        self.emailer = Emailer()

    def set_end_time(self):
        self.end_time = datetime.datetime.now().strftime("%H:%M:%S %d-%m-%Y")

    def clean_up(self):
        pass


class Emailer:

    def __init__(self):
        self.config_json = self.read_json("config.json")

    # https://realpython.com/python-send-email/
    def mail_logs(self):
        pass

    @staticmethod
    def read_json(json_file):
        with open(json_file, "r") as file:
            content = file.read()
            json_data = json.loads(content)
        return json_data


# https://realpython.com/python-send-email/
if __name__ == "__main__":
    main()
