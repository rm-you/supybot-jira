supybot-jira
============

Jira REST API issue plugin for supybot / Limnoria.<br />
The plugin can show the issue summary based on regexp, it can also do a subset of commands on Jira, like commenting on an issue or resolving an issue.<br />
NOTE: This controlling part currently requires OAuth access, so it requires you to be able to link bot as a Jira linked application.
Also, it does not perform user verification so it's not only insecure, but unusable on public networks, unless you control the ident user values of people connecting to the server. Both these can be fixed of cource (TODO).<br />
There also exists a similarly named project by zhangsen, but it appears to be unmaintained for the last year, and uses the now unsupported SOAP API.<br />

<b>Requirements:</b>
```
pip install jira-python<br />
```
python-oauthlib is required for OAuth.
<b>Installation:</b>

Clone this repository into your supybot plugins directory as "Jira".<br />

<b>Configuration:</b>

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
supybot.plugins.Jira.OauthConsumerName = The Consumer Name use in Jira linked applications
supybot.plugins.Jira.OauthConsumerKey  = The Consumer Key use in Jira linked applications
supybot.plugins.Jira.TokenDatabase     = Filename that stores yaml-based user tokens for Jira OAuth
```

For linking Jira with supybot see https://confluence.atlassian.com/display/JIRA/Linking+to+Another+Application

<b>Usage:</b>

The bot is a simple snarfer. Just say anything that includes a valid issue key, and it will attempt a lookup and respond with some basic information.<br />

The default output looks like this:<br />
```
<user> I've just finished up with JRA-123 and moved the code to our Testing environment.
<supybot> (Story JRA-123) Add Pagination [ Philip Fry ] Ready For Test https://jira.mysite.com/browse/JRA-123
```

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
<b>Planned features:</b>

Better, more customizable response patterns.<br />
