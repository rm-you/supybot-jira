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
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from jira.client import JIRA

try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Jira')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

snarfRegex = 'CLB-[0-9]+'

class Jira(callbacks.PluginRegexp):
    """This plugin will automatically snarf Jira ticket numbers, and reply with
    some basic information about the ticket."""
    threaded = True
    regexps = ['getIssue']

    def __init__(self, irc):
        self.__parent = super(Jira, self)
        self.__parent.__init__(irc)
        self.server = self.registryValue('server')
        self.user = self.registryValue('user')
        self.password = self.registryValue('password')
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
            print "Invalid Jira snarf: %s" % issueName
            return

        if issue:
            issuetype = issue.fields.issuetype.name
            key = issue.key
            name = issue.fields.summary
            status = issue.fields.status.name
            time = issue.fields.timeestimate
            if issue.fields.assignee:
                assignee = issue.fields.assignee.displayName
            else:
                assignee = "Unassigned"
            if time:
                hours = time / 60 / 60
                minutes = time / 60 % 60
                displayTime = " / %ih%im" % (hours, minutes)
            else:
                displayTime = ""
            url = ''.join((self.server, '/browse/', key))

            replytext = ("(%s %s) %s [ \x032%s\x03%s ] \x033\x02%s\x02\x03 %s"
                        % (issuetype, key, name, assignee, displayTime, status,
                            url))
            irc.reply(replytext, prefixNick=False)
    getIssue.__doc__ = '(?P<issue>%s)' % snarfRegex

Class = Jira

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
