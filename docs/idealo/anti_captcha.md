## Captcha
2020-03-11 - Amar Hodzic


Each site that uses Captcha gets an "websiteKey" that is a long string.
This website key is the association for Google to know from what website the Captcha was triggered
when you load their Captcha and solve it. The key can be changed but usually websites keep the same.
When you get the Captcha page when surfing, the website key is embedded in the HTML.
Solving the captcha will yield a response string that you "give" to the web page, that then checks if its correct with Google.  

**Example**
<br/>
If you got captcha on site: "https://www.idealo.de/preisvergleich/MainSearchProductCategory.html?q=04548736088818"

Then the response string should be appended with the url in the format:
https://www.idealo.de/preisvergleich/MainSearchProductCategory.html?q=04548736088818&g-recaptcha-response={RESPONSE_KEY}"

### Anti-Captcha

Anti-captcha is a service that solves the captchas for you and returns the response string.
They employ people in India to solve the captchas.
By creating a task and send them the "websiteKey" and URL, they can solve it.
For reCaptcha, it usually took around 50s (maybe possible to get it faster if bid is increased for API calls). Their official SDK for Python seem to be for 2.7. There is a russian guy who has a Github repo supporting 3.6.

<br/>


**Creating tasks**

*An example of creating a task for reCaptha solving using Python Requests library*

```

import requests

headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
}
data = '{"clientKey":"{ANTI_CAPTCHA_API_KEY}","task":{"type":"NoCaptchaTaskProxyless","websiteURL":"https://www.idealo.de/preisvergleich/MainSearchProductCategory.html?q=04548736088818","websiteKey":"6LdAKg4TAAAAACsbrjT4aMumPbLZCz-6pslszlrQ"},"softId":0,"languagePool":"en"}'

response_task = requests.post('https://api.anti-captcha.com/createTask', headers=headers, data=data)

```
*Response from Anti-Captcha*
```
{"errorId":0,"taskId":1301982370}
```
<br/>

**Checking tasks**

*An example of how to check the state of a task sent to Anti-Captcha*

```
import requests

headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
}
data =
{"clientKey":"{ANTI_CAPTCHA_API_KEY}","taskId": 1301982370)
response_solved = requests.post('https://api.anti-captcha.com/getTaskResult', headers=headers, data=data)


```

*Response from Anti-Captcha, two types of replies*
```
{"errorId":0,"status":"processing"}

or

{"errorId":0,"status":"ready","solution":{"gRecaptchaResponse":"03AERD8XqfttopnQvrtup9hsGEFHR32isjCMnH0HY8t5-QBiWUivPcF5XOMczvyuf70GCH5TTLMmBZIANeiRdcnI0TtMmLMHTgxZVXlwGtU_W9GjT8MWsc_fFSR6fic7JzcCn4TNvnzLbeMVDvOW1jQW37UYnnGNfMMpnr-NHiRJrgz5ZgGvXLsZBbusoydjHUykreP3794YGj6meS0eErenOmJbRVLU78XKFfDJvVB-CAmXC2A7FQss9u3kCFxt7NybZ-IyQWWv52Id0ON23EFdQAw_bwkAgU5H8qH03NPCbLDZhTdMxi6k_hVJdzv7mwyETbkWx31i48w0beRCF4-j0WewupJ0om0kTUVBfjSXZIJ7XTHYSYW5Q6jodDL61XT27njrZZXECAEoKYpbheW8lb8mKS3bv9ISrwjrSm66s4nLNBGdaucTPakcGhKUpVJ-1mqfBeeULdQESJtwD_sTgPB4vw1S2CKg"},"cost":"0.002200","ip":"84.17.49.54","createTime":1583420456,"endTime":1583420516,"solveCount":0
```

<br/>
<br/>


**A visualization on the structure of communication between your bot, targetet website, "Anti-Captcha" and Google.**

![Graphical explanation of the flow](https://i.imgur.com/B2X1Tyu.png)

For further documentation visit:

[Anti-Captcha Documentation!](https://anticaptcha.atlassian.net/wiki/spaces/API/pages/578322433/API+Methods)
