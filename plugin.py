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
from oauthlib.oauth1 import SIGNATURE_RSA
from requests_oauthlib import OAuth1Session
import yaml
import os

try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Jira')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x


class OAuth1SessionNoVerify(OAuth1Session):
    def __init__(self, *args, **kwargs):
        self._old_post = self.post
        self.post = self._my_post
        self._verifySSL = kwargs.pop('verify', True)
        super(OAuth1SessionNoVerify, self).__init__(*args, **kwargs)

    def _my_post(self, url):
        return self._old_post(url, verify=self._verifySSL)


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
        self.consumer_name = self.registryValue('OAuthConsumerName')
        self.consumer_key = self.registryValue('OAuthConsumerKey')
        self.oauth_verifier = self.registryValue('OAuthVerifier')
        self.rsa_key_file = self.registryValue('OAuthConsumerSSLKey')
        self.request_token_url = "%s/plugins/servlet/oauth/request-token" % self.server
        self.access_token_url = "%s/plugins/servlet/oauth/access-token" % self.server
        self.authorize_url = "%s/plugins/servlet/oauth/authorize" % self.server
        self.tokenstore = self.registryValue('OAuthTokenDatabase')
        try:
            f = open(self.rsa_key_file)
            self.rsa_key = f.read()
            f.close()
        except:
            print "Cannot access the rsa key file %s" % self.rsa_key_file
            self.rsa_key = None
        try:
            f = open(self.tokenstore)
            self.tokens = yaml.load(f)
            f.close()
        except:
            self.tokens = dict()

        options = { 'server': self.server, 'verify': self.verifySSL }
        self.jira = dict()
        try:
            oauth_dict = {
                'access_token': self.tokens[self.user]['access']['oauth_token'],
                'access_token_secret': self.tokens[self.user]['access']['oauth_token_secret'],
                'consumer_key': self.consumer_key,
                'key_cert': self.rsa_key
            }
            self.jira[self.user] = JIRA(options = options, oauth = oauth_dict)
        except:
            auth = (self.user, self.password)
            self.jira[self.user] = JIRA(options = options, basic_auth = auth)

    def establishConnection(self, user):
        options = { 'server': self.server, 'verify': self.verifySSL }
        oauth_dict = {
           'access_token': self.tokens[user]['access']['oauth_token'],
           'access_token_secret': self.tokens[user]['access']['oauth_token_secret'],
           'consumer_key': self.consumer_key,
           'key_cert': self.rsa_key
        }
        self.jira[user] = JIRA(options = options, oauth = oauth_dict)

    def getIssue(self, irc, msg, match, force=False):
        """Get a Jira Issue"""
        if not ircutils.isChannel(msg.args[0]) and not force:
            return
        if conf.get(conf.supybot.plugins.Jira.lookup, msg.args[0]) == False:
            return
        issueName = match.group('issue')
        try:
            issue = self.jira[self.user].issue(issueName)
        except Exception, e:
            self.log.exception('Error loading issue.', e)
            irc.reply("Cannot find %s bug." % issueName)
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
                        "assignee": _c(assignee, "blue"),
                        "displayTime": displayTime,
                        "url": url,
                    }

            replytext = (self.template % values)
            irc.reply(replytext, prefixNick=False)
    getIssue.__doc__ = '(?P<issue>%s)' % conf.supybot.plugins.Jira.snarfRegex

    def issue(self, irc, msg, args, ticket):
        """<ticket>

        Prints details for a given issue."""
        regex = '(?P<issue>%s)' % conf.supybot.plugins.Jira.snarfRegex
        m = re.search(regex, ticket)
        return self.getIssue(irc, msg, m, force=True)
    issue = wrap(issue, ['text'])

    def comment(self, irc, msg, args, matched_ticket, comment):
        """<ticket> <comment>

        Comments on a given issue."""

        #Get user name. Very simple. Assumes that the data in ident is authoritative and no-one can fake it.
        user = msg.user
        if (self.jira.has_key( user ) != True):
            try:
                self.establishConnection(user)
            except:
                irc.reply("Cannot establish connection. Probably invalid or no token.")
                return

        try:
            if self.jira[user].add_comment(matched_ticket.string, comment):
                irc.reply("OK. Comment created.")
        except Exception as detail:
            irc.reply("Cannot create comment. Error: %s" % detail)
            print "Cannot comment on: %s. Error %s." % ( matched_ticket.string, detail)
            return
    comment = wrap(comment, [('matches', re.compile(str(conf.supybot.plugins.Jira.snarfRegex)), "The first argument should be the ticket number, but it doesn't match the pattern."), 'text'])

    def status(self, irc, msg, args, matched_ticket, newstatus):
        """<ticket> <new status>

        Changes the status of the ticket to the requested one."""
        user = msg.user
        if (self.jira.has_key( user ) != True):
            try:
                self.establishConnection(user)
            except:
                irc.reply("Cannot establish connection. Probably invalid or no token.")
                return
        try:
            issue = self.jira[user].issue(matched_ticket.string)
        except Exception as detail:
            irc.reply("Cannot find %s bug. Error %s." % ( matched_ticket.string, detail ))
            return

        if issue.fields.status.name == newstatus:
            irc.reply("Too late! The %s issue is already in the requested status." % matched_ticket.string)
            return

        try:
            transitions = self.jira[user].transitions(issue)
        except Exception as detail:
            irc.reply("Cannot get transitions states. Error %s." % detail)
            return
        for t in transitions:
            if t['to']['name'] == newstatus:
                try:
                    self.jira[user].transition_issue(issue, t['id'])
                except Exception as detail:
                    irc.reply("Cannot transition to %s. Error %s." % (newstatus, detail))
                    return
                irc.reply("%s successfully changed state to %s" % (matched_ticket.string, newstatus) )
                return
        irc.reply("No transition to %s state possible from the ticket." % newstatus)
    status = wrap(status, [('matches', re.compile(str(conf.supybot.plugins.Jira.snarfRegex)), "The first argument should be the ticket number, but it doesn't match the pattern."), 'text'])

    def ResolveIssue(self, irc, msg, matched_ticket, resolution, comment):
        user = msg.user
        if (self.jira.has_key( user ) != True):
            try:
                self.establishConnection(user)
            except:
                irc.reply("Cannot establish connection. Probably invalid or no token.")
                return
        try:
            issue = self.jira[user].issue(matched_ticket.string)
        except Exception as detail:
            irc.reply("Cannot find %s bug. Error: %s" % (matched_ticket.string, detail))
            return

        if issue.fields.status.name == "Resolved":
            irc.reply("Too late! The %s issue is already resolved." % matched_ticket.string)
            return

        try:
            transitions = self.jira[user].transitions(issue)
        except Exception as detail:
            irc.reply("Cannot get transitions states. Error: %s." % detail)
            return
        for t in transitions:
            if t['to']['name'] == "Resolved":
                try:
                    self.jira[user].transition_issue(issue, t['id'], { "resolution": {"name": resolution} }, comment)
                except Exception as detail:
                    irc.reply("Cannot transition to Resolved. Error %s." % detail)
                    return
                irc.reply("Resolved successfully")
                return
        irc.reply("No transition to Resolved state possible from the ticket.")

    def resolve(self, irc, msg, args, matched_ticket, comment):
        """<ticket> [<comment>]

        Changes the ticket to Resolved state, optionally with a comment."""
        self.ResolveIssue(irc, msg, matched_ticket, "Fixed", comment)
    resolve = wrap(resolve, [('matches', re.compile(str(conf.supybot.plugins.Jira.snarfRegex)), "The first argument should be the ticket number, but it doesn't match the pattern."), optional('text')])

    def wontfix(self, irc, msg, args, matched_ticket, comment):
        """<ticket> [<comment>]

        Changes the ticket to Resolved state with 'Won't fix' resolution, optionally with a comment."""
        self.ResolveIssue(irc, msg, matched_ticket, "Won't Fix", comment)
    wontfix = wrap(wontfix, [('matches', re.compile(str(conf.supybot.plugins.Jira.snarfRegex)), "The first argument should be the ticket number, but it doesn't match the pattern."), optional('text')])

    def assign(self, irc, msg, args, matched_ticket, assignee):
        """<ticket> <assginee>

        Assigns the issue to the given user ID. If no user ID is given, it is assigned to the requester."""

        #Get user name. Very simple. Assumes that the data in ident is authoritative and no-one can fake it.
        user = msg.user
        if (self.jira.has_key( user ) != True):
            try:
                self.establishConnection(user)
            except:
                irc.reply("Cannot establish connection. Probably invalid or no token.")
                return
        if (assignee is None):
            assignee = user
        try:
            self.jira[user].assign_issue(matched_ticket.string, assignee)
            issue = self.jira[user].issue(matched_ticket.string)
            url = ''.join((self.server, '/browse/', issue.key))
            irc.reply("Issue assigned to %s: %s" % (assignee, url))
        except Exception as detail:
            irc.reply("Cannot assign %s to %s. Error %s." % (matched_ticket.string, assignee, detail) )
            return
    assign = wrap(assign, [('matches', re.compile(str(conf.supybot.plugins.Jira.snarfRegex)), "The first argument should be the ticket number, but it doesn't match the pattern."), optional('somethingWithoutSpaces')])

    def unassign(self, irc, msg, args, matched_ticket):
        """<ticket>

        Unassigns the issue."""
        user = msg.user
        if (self.jira.has_key( user ) != True):
            try:
                self.establishConnection(user)
            except:
                irc.reply("Cannot establish connection. Probably invalid or no token.")
                return
        try:
            self.jira[user].assign_issue(matched_ticket.string, None)
            issue = self.jira[user].issue(matched_ticket.string)
            url = ''.join((self.server, '/browse/', issue.key))
            irc.reply("Issue unassigned: %s" % (url,))
        except Exception as detail:
            irc.reply("Cannot unassign %s. Error %s." % (matched_ticket.string, detail) )
            return
    unassign = wrap(unassign, [('matches', re.compile(str(conf.supybot.plugins.Jira.snarfRegex)), "The first argument should be the ticket number, but it doesn't match the pattern.")])


    def create(self, irc, msg, args, matched_proj, issuetype, title):
        """<project> <issue type> <title>

        Creates a new issue in Jira. Should print out the issue number."""

        #Get user name. Very simple. Assumes that the data in ident is authoritative and no-one can fake it.
        user = msg.user
        if (self.jira.has_key( user ) != True):
            try:
                self.establishConnection(user)
            except:
                irc.reply("Cannot establish connection. Probably invalid or no token.")
                return
        try:
            newissue = self.jira[user].create_issue(project={'key': matched_proj.string}, summary=title, issuetype={'name': issuetype})
            irc.reply("OK. %s created." % newissue.key)
        except Exception as detail:
            irc.reply("Cannot create issue. Check the type %s is valid for the project. Error: %s." % (issuetype, detail) )
            print "Cannot comment on: %s" % matched_proj.string
            return
    create = wrap(create, [('matches', re.compile('^[A-Z]+$'), "The first argument should be the project abbrev like JRA, but it doesn't match the pattern."), 'something', 'text'])

    def describe(self, irc, msg, args, matched_ticket, text):
        """<issue> <description>

        Replaces the description of the issue."""

        #Get user name. Very simple. Assumes that the data in ident is authoritative and no-one can fake it.
        user = msg.user
        if (self.jira.has_key( user ) != True):
            try:
                self.establishConnection(user)
            except:
                irc.reply("Cannot establish connection. Probably invalid or no token.")
                return
        try:
            issue = self.jira[user].issue(matched_ticket.string)
            if text:
                issue.update(description = text)
                irc.reply("OK. Description changed.")
            else:
                irc.reply(issue.fields.description)
        except Exception as detail:
            irc.reply("Cannot change issue description. Error %s." % detail)
            return
    describe = wrap(describe, [('matches', re.compile(str(conf.supybot.plugins.Jira.snarfRegex)), "The first argument should be the issue ID like JRA-123, but it doesn't match the pattern."), optional('text')])

    def priority(self, irc, msg, args, matched_ticket, prio):
        """<issue> <priority>

        Sets the priority on the ticket."""

        #Get user name. Very simple. Assumes that the data in ident is authoritative and no-one can fake it.
        user = msg.user
        if (self.jira.has_key( user ) != True):
            try:
                self.establishConnection(user)
            except:
                irc.reply("Cannot establish connection. Probably invalid or no token.")
                return
        try:
            issue = self.jira[user].issue(matched_ticket.string)
            issue.update(priority = { 'id' : str(prio) })
            irc.reply("OK. Priority changed.")
        except Exception as detail:
            irc.reply("Cannot change issue priority. Error %s." % detail)
            return

    priority = wrap(priority, [('matches', re.compile(str(conf.supybot.plugins.Jira.snarfRegex)), "The first argument should be the issue ID like JRA-123, but it doesn't match the pattern."), 'int'])

    def watch(self, irc, msg, args, matched_ticket):
        """<issue>

        Adds the requester to the watchers list."""

        #Get user name. Very simple. Assumes that the data in ident is authoritative and no-one can fake it.
        user = msg.user
        if (self.jira.has_key( user ) != True):
            try:
                self.establishConnection(user)
            except:
                irc.reply("Cannot establish connection. Probably invalid or no token.")
                return

        try:
            self.jira[user].add_watcher(issue = matched_ticket.string, watcher = user)
            irc.reply("OK. Watchers list modifed.")
        except Exception as detail:
            irc.reply("Cannot modfidy the watchers list. Error: %s." % detail)
            return
    watch = wrap(watch, [('matches', re.compile(str(conf.supybot.plugins.Jira.snarfRegex)), "The first argument should be the issue ID like JRA-123, but it doesn't match the pattern.")])

    def unwatch(self, irc, msg, args, matched_ticket):
        """<issue>

        Removes the requestor from the watchers list."""

        #Get user name. Very simple. Assumes that the data in ident is authoritative and no-one can fake it.
        user = msg.user
        if (self.jira.has_key( user ) != True):
            try:
                self.establishConnection(user)
            except:
                irc.reply("Cannot establish connection. Probably invalid or no token.")
                return

        try:
            self.jira[user].remove_watcher(issue = matched_ticket.string, watcher = user)
            irc.reply("OK. Watchers list modified.")
        except Exception as detail:
            irc.reply("Cannot change the watchers list. Error: %s." %detail)
            return
    unwatch = wrap(unwatch, [('matches', re.compile(str(conf.supybot.plugins.Jira.snarfRegex)), "The first argument should be the issue ID like JRA-123, but it doesn't match the pattern.")])

    def issues(self, irc, msg, args, search_text):
        """<search_text>

        Searches Jira issue summaries for <search_text>.
        """
        replies = []
        issues = self.jira[self.user].search_issues("summary ~ {0}".format(search_text))
        for issue in issues:
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
                        "assignee": _c(assignee, "blue"),
                        "displayTime": displayTime,
                        "url": '',
                    }
            replies.append(self.template % values)
        irc.reply('|| '.join(replies), prefixNick=False)
        return
    issues = wrap(issues, ['text'])

    def gettoken(self, irc, msg, args, force):
        """

        Requests an OAuth token for the bot so that it can act in the name of the user."""
        if (force != None and force != "force"):
            irc.reply("Wrong syntax.")
            return

        #Get user name. Very simple. Assumes that the data in ident is authoritative and no-one can fake it.
        user = msg.user

        try:
            if (self.tokens[user].has_key('access_key') and force != "force"):
                irc.reply("You seem to already have a token. Use force to get a new one.")
                return
            if (self.tokens[user].has_key('request_key') and force != "force"):
                irc.reply("You have requested a token already. If you accepted access to Jira, use 'committoken' Use 'gettoken force' to request a new token.",private=True,notice=False)
                return
        except:
            self.tokens[user] = dict()
            self.tokens[user]['request'] = dict()

        oauth = OAuth1SessionNoVerify(
                    self.consumer_key,
                    signature_type='auth_header',
                    signature_method=SIGNATURE_RSA,
                    rsa_key=self.rsa_key,
                    verify=self.verifySSL
                )
        try:
            request_token = oauth.fetch_request_token(self.request_token_url)
        except Exception as detail:
            irc.reply("Error occurred while getting token: %s." %detail)
            return

        irc.reply("Please go to %s?oauth_token=%s" % (self.authorize_url, request_token['oauth_token']), private=True, notice=False)
        irc.reply("After that's done, use the bot command 'committoken'", private=True, notice=False)

        self.tokens[user]['request'] = request_token

        f = file("%s.new" % self.tokenstore,'w')
        yaml.dump(self.tokens, f, default_flow_style=False)
        os.rename("%s.new" % self.tokenstore, self.tokenstore)

    gettoken = wrap(gettoken, [ optional('text') ])

    def committoken(self, irc, msg, args):
        """takes no arguments.

        Tells the bot that the requested token is accepted."""

        #Get user name. Very simple. Assumes that the data in ident is authoritative and no-one can fake it.
        user = msg.user

        try:
            if ( self.tokens[user].has_key('request') != True):
                irc.reply("No request token found. You need to first request a token with 'gettoken'.",private=True,notice=False)
                return
        except:
            irc.reply("No request token found. You need to first request a token with 'gettoken'.",private=True,notice=False)
            return

        oauth = OAuth1SessionNoVerify(
                    self.consumer_key,
                    signature_type='auth_header',
                    signature_method=SIGNATURE_RSA,
                    rsa_key=self.rsa_key,
                    verifier=self.oauth_verifier,
                    verify=self.verifySSL
                )
        oauth._populate_attributes(self.tokens[user]['request'])

        try:
            self.tokens[user]['access'] = oauth.fetch_access_token(self.access_token_url)
        except Exception as detail: 
            irc.reply("Error occured while committing token: %s." % detail)

        irc.reply("Token committed.", private=True, notice=False)

        f = file("%s.new" % self.tokenstore,'w')
        yaml.dump(self.tokens, f, default_flow_style=False)
        os.rename("%s.new" % self.tokenstore, self.tokenstore)

    committoken = wrap(committoken)

def _b(text):
    return ircutils.bold(text)

def _c(text, color):
    return ircutils.mircColor(text, color)

Class = Jira

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
