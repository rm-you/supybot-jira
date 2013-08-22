supybot-jira
============

Jira REST API issue snarfer plugin for supybot / Limnoria.
There also exists a similarly named project by zhangsen, but it appears to be unmaintained for the last year, and uses the now unsupported SOAP API.

<b>Requirements:</b>

pip install jira-python

<b>Installation:</b>

Clone this repository into your supybot plugins directory as "Jira".

<b>Configuration:</b>

You will need to configure the following:

supybot.plugins.Jira.server = The server name of your Jira instance. (ex: "https://jira.mysite.com")
supybot.plugins.Jira.user   = A username on the Jira instance. (ex: "project-bot")
supybot.plugins.Jira.password = The password for the configured username.
supybot.plugins.Jira.verifySSL = If your domain's SSL certificate is invalid, this must be set to false.
supybot.plugins.Jira.template = The output format used when the plugin replies to queries -- fairly limited right now.
supybot.plugins.Jira.snarfRegex = The regular expression used for snarfing Jira issues in chat. The whole of this expression is what the plugin will use to look up your issue in Jira. When setting this from within IRC, you will probably need to use double-quotes or the bot will fail to handle your input. (ex: "JRA-[0-9]+")

<b>Usage:</b>

Right now, the bot is a simple snarfer. Just say anything that includes a valid issue key, and it will attempt a lookup and respond with some basic information.

The default output looks like this:

<user> I've just finished up with JRA-123 and moved the code to our Testing environment.
<supybot> (Story JRA-123) Add pagination to the user list [ <font color="blue">Adam Harwell</font> ] <font color="green"><b>Ready For Test</b></font> <a>https://jira.mysite.com/browse/JRA-123</a>

<b>Planned features:</b>

Better, more customizable response patterns.
