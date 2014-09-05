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

import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Jira')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

template = "(%(type)s %(key)s) %(summary)s [ %(assignee)s%(displayTime)s ] "\
           "%(status)s %(url)s"

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    Jira = conf.registerPlugin('Jira', True)
    server = something("""What is the URL for the Jira instance?""")
    user = something("""What is the username for the Jira user?""")
    password = something("""What is the password for the Jira user?""")
    template = something("""What output template would you like?""",
            default=template)
    snarfRegex = something("""What is the prefix for your Jira issue keys?""",
            default="CLB")
    snarfRegex = ''.join((snarfRegex, '-[0-9]+'))
    verifySSL = yn("""Would you like the plugin to verify your Jira instance's
            SSL certificate?""", default=False)
    OAuthConsumerName = something("""What is the consumer name as per the Jira linked applications?""")
    OAuthConsumerKey = something("""What is the consumer secret key as per the Jira linked applications?""")
    OAuthConsumerSSLKey = something("""What is the filename holding the SSL key bound with the Jira trusted cert?""")

    Jira.server.setValue(server)
    Jira.user.setValue(user)
    Jira.password.setValue(password)
    Jira.template.setValue(template)
    Jira.snarfRegex.setValue(snarfRegex)
    Jira.verifySSL.setValue(verifySSL)
    Jira.OAuthConsumerName.setValue(OauthConsumerName)
    Jira.OAuthConsumerKey.setValue(OauthConsumerKey)
    Jira.OAuthConsumerSSLKey.setValue(OauthConsumerSSLKey)

    #snarfRegex = expect("""What is the regex for your Jira ticket IDs?""", 
    #                        default="JRA-[0-9]+")
    #Jira.snarfRegex.setValue(snarfRegex)

Jira = conf.registerPlugin('Jira')

conf.registerGlobalValue(Jira, 'server', 
	registry.String('', _("""URL for Jira instance.""")))
conf.registerGlobalValue(Jira, 'user', 
	registry.String('', _("""Username for Jira authentication.""")))
conf.registerGlobalValue(Jira, 'password', 
	registry.String('', _("""Password for Jira authentication.""")))
conf.registerGlobalValue(Jira, 'template', 
	registry.String(template, 
        _("""Template for the plugin's output formatting.""")))
conf.registerGlobalValue(Jira, 'verifySSL',
    registry.Boolean(False, _("""Verify SSL certificate for Jira instance.""")))
conf.registerGlobalValue(Jira, 'snarfRegex', 
    registry.String('JRA-[0-9]+', _("""Regex for Jira ticket ID snarfing.""")))
conf.registerGlobalValue(Jira, 'OAuthConsumerName', 
	registry.String('', _("""Consumer name as per the Jira linked applications."""), private=True))
conf.registerGlobalValue(Jira, 'OAuthConsumerKey', 
	registry.String('', _("""Consumer secret key as per the Jira linked applications."""), private=True))
conf.registerGlobalValue(Jira, 'OAuthConsumerSSLKey', 
	registry.String('', _("""Filename holding the SSL key bound with the Jira trusted cert."""), private=True))
conf.registerGroup(Jira, 'tokens')

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
