# using SendGrid's Python Library
# https://github.com/sendgrid/sendgrid-python
import sendgrid
import os
from sendgrid.helpers.mail import *

# sg = sendgrid.SendGridAPIClient(apikey=os.environ.get('SENDGRID_API_KEY'))
sg = sendgrid.SendGridAPIClient(apikey= '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')
from_email = Email("frankwang.alert@gmail.com")
# to_email = Email("frankwang.alert@gmail.com", "frankwang.trading@gmail.com")
to_email = Email('2242178683@vtext.com')
subject = "test sendgrid 04"
content = Content("text/plain", "dddd")
mail = Mail(from_email, subject, to_email, content)
response = sg.client.mail.send.post(request_body=mail.get())
print(response.status_code)
print(response.body)
print(response.headers)