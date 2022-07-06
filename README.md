# youtrack-issue-generator
This is a python script designed to create issues on Jetbrains YouTrack. 

# Installation/Usage on Linux Server
1. Clone the repo to a location of choice. 
2. Edit `config.json` as follows.
   1. `youtrack-token` - This is the permanent token you need to generate from YouTrack. For more information see [YouTrack's documentation](https://www.jetbrains.com/help/youtrack/devportal/Manage-Permanent-Token.html#obtain-permanent-token).
   2. `youtrack-api-url` - This is the url to access your instance of YouTrack.
   Example: `https://example.myjetbrains.com/youtrack/` if using cloud instance.
   3. `smtp-username` - This is the username used for authorising with the `smtp` server used to send the notification email.
   4. `smtp-password` - This is the password used for authorising with the `smtp` server.
   5. `smtp-sender-email` - This is the email that the notification will be sent from.
   6. `smtp-receiver-email` - This is the email the notification will be sent to.
3. Edit `issues.json` as follows.
   1. `date` - This field sets the date which this issue will be generated. Please note, incorrectly formatted dates will cause the issue to not be generated. The accepted values are as follows:
      1. `patch-tuesday` - This will create the issue on the second tuesday of the month. 
      2. `saturday-after-patch-tuesday` - This will create the issue on the saturday after the patch tuesday (second tuesday of the month).
      3. `31-01` - This will create the issue every year on the specified day and month. Use format `DD-MM` (with leading 0).
      4. `31-01-2020` - This will create a ticket on a specific day on a specific year. Use format `DD-MM-YYYY` (with leading 0).
      5. `1-31` - This will create the issue on the specified day every month. (Please note it is `int` value, see first template issue in `issues.json`.)
      6. `daily` - This will create the issue every day.
      7. `weekly` - This will create a weekly issue based on the day of the week.
   2. `day-of-week` - This field is required when you have `date` field set to `weekly`.
      1. `1-7` - Set an `int` value of 1 to 7. (1 = Monday & 7 = Sunday)
   3. `project` - This field selects the project to add the issue to. Please enter the project ID (prefix of issue IDs).
   4. `summary` - This field sets the summary field of the issue on YouTrack.
   5. `description` - This field sets the description field of the issue on YouTrack.
   6. `custom-fields` - This field sets the values of custom fields you have for the project on YouTrack. This will be project specific, please see first template issue in `issues.json` to see how it is structured.
4. Open `/etc/crontab` and add the following:
   1. `0 6 * * * username python /path/to/issue-generator.py`
   This will ensure the script to run at 6am every day, you can update it to run at a time of your choice.
      1. Change `username` to the user you would like the script to be run by.
      2. Change `/path/to/issue-generator.py` to the full path to the file.
      3. Ensure `python` is python 3.x and not 2.x.
         1. You can check by running `python --version`. If it shows as 2.x, you can run `sudo apt install python-is-python3` if you have administrator privileges. Alternatively, you can update crontab from `python` to `python3`.

