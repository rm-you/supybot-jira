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
import supybot.registry as registry
from requests_oauthlib import OAuth1
from oauthlib.oauth1 import SIGNATURE_RSA
import oauth2 as oauth

try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Jira')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

class Jira(callbacks.PluginRegexp):
    """This plugin communicates with Jira. It will automatically snarf
    Jira ticket numbers, and reply with some basic information
    about the ticket. It can also close and comment on Jira tasks."""
    threaded = True
    unaddressedRegexps = ['getIssue']
    flags = 0

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
            try:
                assignee = issue.fields.assignee.displayName
            except:
                assignee = "Unassigned"

            try:
                time = issue.fields.timeestimate
                hours = time / 60 / 60
                minutes = time / 60 % 60
                displayTime = " / %ih%im" % (hours, minutes)
            except:
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

    def ResolveIssue(self, irc, matched_ticket, resolution, comment):
        irc.reply("attempts to close issue %s." % matched_ticket.string, action=True)
        try:
            issue = self.jira.issue(matched_ticket.string)
        except:
            irc.reply("cannot find %s bug" % matched_ticket.string, action=True)
            print "Invalid Jira snarf: %s" % matched_ticket.string
            return

        if issue.fields.status.name == "Resolved":
            irc.reply("Too late! The %s issue is already resolved." % matched_ticket.string)
            return

        try:
            transitions = self.jira.transitions(issue)
        except:
            irc.reply("cannot get transitions states")
            return
        for t in transitions:
            if t['to']['name'] == "Resolved":
                try:
                    self.jira.transition_issue(issue, t['id'], { "resolution": {"name": resolution} }, comment)
                except:
                    irc.reply("Cannot transition to Resolved")
                    return
                irc.reply("Resolved successfully")
                return
        irc.reply("No transition to Resolved state possible from the ticket.")

    def resolve(self, irc, msg, args, matched_ticket, comment):
        """<ticket> <comment> takes ticket ID-number and optionally closing comment

        Should return nothing, but might if bad things happen."""
        self.ResolveIssue(irc, matched_ticket, "Fixed", comment)
    resolve = wrap(resolve, [('matches', re.compile(str(conf.supybot.plugins.Jira.snarfRegex)), "The first argument should be the ticket number, but it doesn't match the pattern."), optional('text')])

    def wontfix(self, irc, msg, args, matched_ticket, comment):
        """<ticket> <comment> takes ticket ID-number and optionally closing comment

        Should return nothing, but might if bad things happen."""
        self.ResolveIssue(irc, matched_ticket, "Won't Fix", comment)
    wontfix = wrap(wontfix, [('matches', re.compile(str(conf.supybot.plugins.Jira.snarfRegex)), "The first argument should be the ticket number, but it doesn't match the pattern."), optional('text')])

    def gettoken(self, irc, msg, args, force):
        """takes no arguments, or 'force' to override old token

        Requests an OAuth token for the bot so that it can act in the name of the user."""
        if (force != None and force != "force"):
            irc.reply("Wrong syntax.")
            return

        #Get user name. Very simple. Assumes that the data in ident is authoritative and no-one can fake it.
        user = msg.user

        try:
            usertoken = conf.supybot.plugins.Jira.tokens.get(user)
            if (force != "force"):
                irc.reply("You seem to already have a token. Use force to get a new one.")
                return
        except:
            pass


        consumer_name = conf.supybot.plugins.Jira.OAuthConsumerName
        consumer_key = conf.supybot.plugins.Jira.OAuthConsumerKey
        request_token_url = "%s/plugins/servlet/oauth/request-token" % conf.supybot.plugins.Jira.server
        access_token_url = "%s/plugins/servlet/oauth/access-token" % conf.supybot.plugins.Jira.server
        authorize_url = "%s/plugins/servlet/oauth/authorize" % conf.supybot.plugins.Jira.server


        consumer = oauth.Consumer(consumer_key, consumer_name)
        client = oauth.Client(consumer)
        client.set_signature_method(SignatureMethod_RSA_SHA1())
        resp, content = client.request(request_token_url, "POST")
        if resp['status'] != '200':
            irc.msg("Invalid response from Jira %s: %s" % (resp['status'],  content))
            return
        request_token = dict(urlparse.parse_qsl(content))
        irc.msg("Please go to %s?oauth_token=%s" % (authorize_url, request_token['oauth_token']), private=True, notice=False)
        irc.msg("After that's done, use the bot command 'committoken'", private=True, notice=False)

        usertoken = conf.registerGroup(conf.supybot.plugins.Jira.tokens, user)
        usertoken.registerGlobalValue( "request_token",
            registry.String(request_token['oauth_token'], "%s request token" % user, private=True ))
        usertoken.registerGlobalValue( "request_token_secret",
            registry.String(request_token['oauth_token_secret'], "%s request token secret" % user, private=True ))

        irc.reply("Sorry. Not implemented yet.")
    gettoken = wrap(gettoken, [ optional('text') ])

    def committoken(self, irc, msg, args):
        """takes no arguments.

        Tells the bot that the requested token is fine."""
        irc.reply("Sorry. Not implemented yet.")
    committoken = wrap(committoken)

def _b(text):
    return ircutils.bold(text)

def _c(text, color):
    return ircutils.mircColor(text, color)

Class = Jira

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
