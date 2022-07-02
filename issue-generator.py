import calendar

import requests
import sys
import json
import smtplib
import ssl
import datetime


def main():
    issueGenerator = IssueGenerator()
    issueGenerator.find_patch_tuesday()

class IssueGenerator:
    def __init__(self):
        self.token = 0
        self.issues = 9
        self.projects = 0

    def readJson(self):
        with open("daily.json", "r") as file:
            content = file.read()
            jsonData = json.loads(content)

    def mail_logs(self):
        pass

    def find_patch_tuesday(self):
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
