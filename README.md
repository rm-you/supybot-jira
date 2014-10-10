# supybot-jira

Jira REST API issue plugin for supybot / Limnoria.<br />
The plugin can show the issue summary based on regexp, it can also do a subset of commands on Jira, like commenting on an issue or resolving an issue.<br />
NOTE: This controlling part currently requires OAuth access, so it requires you to be able to link bot as a Jira linked application.
Also, it does not perform user verification so it's not only insecure, but unusable on public networks, unless you control the ident user values of people connecting to the server. Both these can be fixed of cource (TODO).<br />
There also exists a similarly named project by zhangsen, but it appears to be unmaintained for the last year, and uses the now unsupported SOAP API.<br />

## Requirements
```
pip install jira-python
```
python-oauthlib is required for OAuth.

## Installation

Clone this repository into your supybot plugins directory as "Jira".<br />

## Configuration

You will need to configure the following:<br />
```
supybot.plugins.Jira.server            = The server name of your Jira instance. (ex: "https://jira.mysite.com")
supybot.plugins.Jira.user              = A username on the Jira instance. (ex: "project-bot")
supybot.plugins.Jira.password          = The password for the configured username. Optional once the bot user has OAuth token.
supybot.plugins.Jira.verifySSL         = If your domain's SSL certificate is invalid, this must be set to false.
supybot.plugins.Jira.template          = The output format used when the plugin replies to queries - fairly limited right now.
supybot.plugins.Jira.snarfRegex        = The regular expression used for snarfing Jira issues in chat. The whole of this
                                         expression is what the plugin will use to look up your issue in Jira. 
                                         When setting this from within IRC, you will probably need to use double-quotes 
                                         or the bot will fail to handle your input.
                                         (ex: "(?:(?<=\\s)|^)[A-Z]+-[0-9]+(?:(?=[\\s.?!,])|$) - Capital letters dash numbers")
supybot.plugins.Jira.OAuthConsumerName = The Consumer Name use in Jira linked applications
supybot.plugins.Jira.OAuthConsumerKey  = The Consumer Key use in Jira linked applications
supybot.plugins.Jira.OAuthVerifier     = The Consumer Verifier string for Jira OAuth
supybot.plugins.Jira.OAuthConsumerSSLKey    = The RSA Private Key use for handling tokens
supybot.plugins.Jira.OAuthTokenDatabase     = Filename that stores yaml-based user tokens for Jira OAuth
```

## Usage

The bot is a simple snarfer. Just say anything that includes a valid issue key, and it will attempt a lookup and respond with some basic information.<br />

The default output looks like this:<br />
```
<user> I've just finished up with JRA-123 and moved the code to our Testing environment.
<supybot> (Story JRA-123) Add Pagination [ Philip Fry ] Ready For Test https://jira.mysite.com/browse/JRA-123
```

## Using OAuth Features
This is a bit complicated, and the JIRA docs aren't especially useful. If you'd like to read them, they're available here:  https://confluence.atlassian.com/display/JIRA/Linking+to+Another+Application

OAuthConsumerName, OAuthConsumerKey, and OAuthConsumerSSLKey must be set, and they are configured in the Incoming Authentication section of the Jira Application Link. When creating an Application Link, just fill in random data (none of it will matter) on the original screen, then click OK and click Edit next to the new Link. You can go to Outgoing Authentication and click "Delete" because this plugin does not use it at all. Click on "Incoming Authentication" and provide a Consumer Key and Consumer Name (which map to the plugin's config variables of the same name) and an RSA public key (not in SSH format). Callback URL should remain empty and 2-Legged OAuth is not required.

OAuthConsumerSSLKey is the *private key* corresponding to the public key you provided to Jira in the Link configuration. The base of your supybot directory (ie, where your main configuration is located) is the root directory, so "id_rsa" would refer to "<supybot_directory>/id_rsa".

OAuthVerifier is (I believe) an additional security layer that is probably off by default. Only set it if you know what you're doing, or you get an error about an incorrect verifier.

OAuthTokenDatabase should be OK to leave as the default value.

Once you set up linked application in Jira, you can perform this kind of chat with supybot (private chat):
```
<user> comment JRA-123 My new comment.
<supybot> Cannot establish connection. Probably invalid or no token.
<user> gettoken
<supybot> Please go to http://someurl.jira.com/plugins/servlet/oauth/authorize?oauth_token=longoauthtokenhashedshowshere
<supybot> After that's done, use the bot command 'committoken'
* user goes to the URL with his browser, logs in to Jira, and clicks Accept
<user> committoken
<supybot> Looks good
<user> comment JRA-123 My new comment.
<supybot> OK
<user> resolve JRA-123
* pybot attempts to close issue JRA-123
<pybot> user: Resolved successfully
```
## Planned features

Better, more customizable response patterns.<br />
