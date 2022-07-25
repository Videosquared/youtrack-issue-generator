# YouTrack Issue Generator
This is a python script designed to create issues on Jetbrains YouTrack on based on the dates set in the configuration. It is designed to be run once a day, and it will generate the corresponding issues for that day. For example, it can generate an issue on every patch tuesday, saturday after patch tuesday, specific date etc... see installation guide below for more details.

NOTE: Many values in the installation guide below **MUST** be entered as is (correctly, case-sensitive) or your issue will not be parsed correctly and not generated.

# Installation/Usage on Linux Server
1. Clone the repo to a location of choice (or download the files).
2. Edit `config.json` as follows.
   1. `youtrack-token` - This is the permanent token you need to generate from YouTrack. Ensure the token owner has access to the projects you wish to create an issue for. For more information see [YouTrack's documentation](https://www.jetbrains.com/help/youtrack/devportal/Manage-Permanent-Token.html#obtain-permanent-token).
   2. `youtrack-api-url` - This is the url to access your instance of YouTrack.
   Example: `https://example.myjetbrains.com/youtrack/` if using cloud instance.
   3. `smtp-server` - This is the address of the smtp server you wish to use.
   4. `smtp-server-port` - This is the SSL port the smtp server listens on (default SSL port is 465).
   5. `smtp-username` - This is the username used for authenticating with the `smtp` server.
   6. `smtp-password` - This is the password used for authenticating with the `smtp` server.
   7. `smtp-sender-email` - This is the email that the notification will be sent from.
   8. `smtp-receiver-email` - This is the email which the notification will be sent to.
3. Edit `issues.json` as follows.
   1. `date` - This field sets the date which this issue will be generated. Please note, incorrectly formatted dates will cause the issue to not be generated. The accepted values are as follows:
      1. `patch-tuesday` - This will create the issue on the second tuesday of the month. 
      2. `saturday-after-patch-tuesday` - This will create the issue on the saturday after the patch tuesday (second tuesday of the month).
      3. `31-01` - This will create the issue every year on the specified day and month. Use format `DD-MM` (with leading 0).
      4. `31-01-2020` - This will create a ticket on a specific day on a specific year. Use format `DD-MM-YYYY` (with leading 0).
      5. `1`-`31` - This will create the issue on the specified day every month. (Please note it is `int` value, see first template issue in `issues.json`.)
      6. `daily` - This will create the issue every day.
      7. `weekly` - This will create a weekly issue based on the day of the week.
   2. `day-of-week` - (OPTIONAL) This field is **REQUIRED** when you have `date` field set to `weekly`.
      1. `1`-`7` - Set an `int` value of 1 to 7. (1 = Monday & 7 = Sunday)
   3. `project` - This field selects the project to add the issue to. Enter the project ID (prefix of issue IDs). 
   Note, `TEMPLATE-PROJECT` is a reserved value and **NO** issues will be generated if `TEMPLATE-PROJECT` is set in the `project` field. 
   4. `summary` - This sets the summary field of the issue on YouTrack.
   5. `description` - This sets the description field of the issue on YouTrack.
   6. `custom-fields` - (OPTIONAL) This sets the values of custom fields you have for the project on YouTrack. This will be project specific, see first template issue in `issues.json` to see how it can be structured. 
   (**ENSURE ALL** custom field names **AND** values are correct to what it is on YouTrack otherwise the issue will **NOT** be generated)
4. Open `/etc/crontab` and add the following:
   1. `0 6 * * * username python /path/to/issue-generator.py`
   This will ensure the script to run at 6am every day, you can update it to run at a time of your choice.
      1. Change `username` to the user you would like the script to be run by.
      2. Change `/path/to/issue-generator.py` to the full path to the file.
      3. Ensure `python` is python 3.x and not 2.x.
         1. You can check by running `python --version`. If it shows as 2.x, you can run `sudo apt install python-is-python3` if you have administrator privileges. Alternatively, you can update crontab from `python` to `python3`.

