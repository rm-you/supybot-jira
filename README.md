supybot-jira
============

Jira REST API issue snarfer plugin for supybot / Limnoria

<b>Requirements:</b>

pip install jira-python

<b>Installation:</b>

Clone this repository into your supybot plugins directory as "Jira".
Edit "plugin.py" and change "snarfRegex" to match your Jira project's ticket codes.

<b>Usage:</b>

Right now, the bot is a simple snarfer. Just say anything that includes a valid ticket code, and it will attempt a lookup and respond with some basic information.

<b>Planned features:</b>

Easily customizable response patterns.
