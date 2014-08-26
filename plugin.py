###
# Copyright (c) 2013, Adam Harwell
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
import supybot.conf as conf
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from jira.client import JIRA
import re

try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Jira')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

snarfRegex = 'CLB-[0-9]+'

class Jira(callbacks.PluginRegexp):
    """This plugin communicates with Jira. It will automatically snarf
    Jira ticket numbers, and reply with some basic information
    about the ticket. It can also close and comment on Jira tasks."""
    threaded = True
    regexps = ['getIssue']

    def __init__(self, irc):
        self.__parent = super(Jira, self)
        self.__parent.__init__(irc)
        self.server = self.registryValue('server')
        self.user = self.registryValue('user')
        self.password = self.registryValue('password')
        self.template = self.registryValue('template')
        self.verifySSL = self.registryValue('verifySSL')
        options = { 'server': self.server, 'verify': self.verifySSL }
        auth = (self.user, self.password)
        self.jira = JIRA(options = options, basic_auth = auth)

    def getIssue(self, irc, msg, match):
        """Get a Jira Issue"""
        if not ircutils.isChannel(msg.args[0]):
            return
        issueName = match.group('issue')
        try:
            issue = self.jira.issue(issueName)
        except:
            irc.reply("cannot find %s bug" % issueName, action=True)
            print "Invalid Jira snarf: %s" % issueName
            return

        if issue:
            if issue.fields.assignee:
                assignee = issue.fields.assignee.displayName
            else:
                assignee = "Unassigned"

            time = issue.fields.timeestimate
            if time:
                hours = time / 60 / 60
                minutes = time / 60 % 60
                displayTime = " / %ih%im" % (hours, minutes)
            else:
                displayTime = ""

            url = ''.join((self.server, '/browse/', issue.key))

            values = {  "type": issue.fields.issuetype.name,
                        "key": issue.key,
                        "summary": issue.fields.summary,
                        "status": _c(_b(issue.fields.status.name), "green"),
                        "assignee": _c(assignee, "light blue"),
                        "displayTime": displayTime,
                        "url": url,
                    }

            replytext = (self.template % values)
            irc.reply(replytext, prefixNick=False)
    getIssue.__doc__ = '(?P<issue>%s)' % conf.supybot.plugins.Jira.snarfRegex

    def comment(self, irc, msg, args, matched_ticket, comment):
        """<ticket> <comment> takes ticket ID-number and the comment

        Should return nothing, but might if bad things happen."""

        try:
            if self.jira.add_comment(matched_ticket.string, comment):
                irc.reply("OK")
        except:
            irc.reply("cannot comment")
            print "Cannot comment on: %s" % matched_ticket.string
            return
    comment = wrap(comment, [('matches', re.compile(str(conf.supybot.plugins.Jira.snarfRegex)), "The first argument should be the ticket number, but it doesn't match the pattern."), 'text'])

    def resolve(self, irc, msg, args, matched_ticket, comment):
        """<ticket> <comment> takes ticket ID-number and optionally closing comment

        Should return nothing, but might if bad things happen."""

        irc.reply("attempts to close issue %s." % matched_ticket.string, action=True)
        try:
            issue = self.jira.issue(matched_ticket.string)
        except:
            irc.reply("cannot find %s bug" % matched_ticket.string, action=True)
            print "Invalid Jira snarf: %s" % matched_ticket.string
            return
        try:
            transitions = self.jira.transitions(issue)
        except:
            irc.reply("cannot get transitions states")
            return
        for t in transitions:
            if t['to']['name'] == "Resolved":
                try:
                    self.jira.transition_issue(issue, t['id'], { "resolution": {"name": "Fixed"} }, comment)
                except:
                    irc.reply("Cannot transition to Resolved")
                    return
                irc.reply("Resolved successfully")
                return
        irc.reply("No transition to Resolved state possible from the ticket.")
    resolve = wrap(resolve, [('matches', re.compile(str(conf.supybot.plugins.Jira.snarfRegex)), "The first argument should be the ticket number, but it doesn't match the pattern."), optional('text')])
#    resolve = wrap(resolve, ['something', 'text'])

def _b(text):
    return ircutils.bold(text)

def _c(text, color):
    return ircutils.mircColor(text, color)

Class = Jira

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
