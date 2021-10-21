<h1 align="center"> <img height="100px" src="https://cdn.discordapp.com/attachments/859335247547990026/900632166935961651/mailhook.png"> </h1>

<h1 align="center"> MailHook </h1>
<h3 align="center"> Modern modmail for modern Discord servers. </h3>

## 🎉 Features

- Completely customizable from the dashboard.
- Full slash commands and context menu commands support.
- Multiprefix support (upto 10 prefixes).
- Per guild configuration.
- Fast response time.

## 💻 How to selfhost?

1. Close the repo:
    ```bash
    $ git clone https://github.com/DeveloperJosh/MailHook
    ```

2. Install Modules.

    ```bash
    # Linux/macOS
    $ python3 -m pip install -r requirements.txt

    # Windows
    $ py -3 -m pip install -r requirements.txt
    ```

3. Setup the `config.py` file.

4. Setup the a `.env` file:
    ```
    DISCORD_BOT_SECRET=Token here
    DATABASE_LINK=Mongo link
    ```
    MongoDB - https://www.mongodb.com/ \
    Discord bot token - https://discord.com/developers/applications

5. Run the bot:
    ```bash
    # Linux/MacOS
    $ python3 main.py

    # Windows
    $ py main.py
    ```

6. Enjoy:
    ![](https://cdn.discordapp.com/attachments/859335247547990026/889350297590333520/unknown.png)

## 🤝 Selfhosting agreement


- You are not allowed to remove the names in the credit command.
- You are not allowed to use the name or the logo of the original bot.
- If you want any ideas/commands added to the bot please tell me [here](https://github.com/DeveloperJosh/MailHook/discussions/2)
- If you need help with the setup [join our discord](https://discord.gg/j99syeQDQk)

## 🖥️ Commands
```
/setup - Setup modmail for your server.
/edit-config - Edit the current modmail configuration.
/show-config - Get the current config.
/start-ticket - Start a ticket with a user.
/close-ticket - Close this ticket.
/modmail-tickets - View all the current modmail tickets.
/anon-reply - Reply anonymously to a ticket.
```

## 👀 Preview

![](https://i.imgur.com/Lv03mou.png)
![](https://i.imgur.com/J7a1FOi.png)
![](https://cdn.discordapp.com/attachments/859335247547990026/889355567339028490/unknown.png)
![](https://cdn.discordapp.com/attachments/859335247547990026/889355834746867783/unknown.png)
![](https://cdn.discordapp.com/attachments/859335247547990026/889355924819542057/unknown.png)

## 🔗 Useful Links

- [Dashboard](https://mail-hook.site)
- [Support Server](https://discord.gg/TeSHENet9M)
- [Invite Me](https://discord.com/oauth2/authorize?client_id=781639675868872796&permissions=8&scope=bot%20applications.commands)
