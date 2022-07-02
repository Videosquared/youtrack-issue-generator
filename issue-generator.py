import calendar
import requests
import sys
import json
import smtplib
import ssl
import datetime


def main():
    issueGenerator = IssueGenerator()


class IssueGenerator:

    def __init__(self):
        self.debug = False
        self.token = 0
        self.issues = 9
        self.projects = 0
        self.config_json = self.read_json("config.txt")
        self.issues_json = self.read_json("issues.json")
        self.logs = []

    def generate(self):
        pass

    def check_date(self):
        pass

    def create_issue(self):
        pass

    def set_custom_fields(self):
        pass

    # https://realpython.com/python-send-email/
    def mail_logs(self):
        pass

    @staticmethod
    def read_json(file):
        with open(file, "r") as file:
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


# https://realpython.com/python-send-email/
if __name__ == "__main__":
    main()
