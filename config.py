import os
from dotenv import load_dotenv

load_dotenv()


class Emojis:
    def __init__(self):
        self.staff = '<:staff:884477446018199552>'
        self.yes = '<:yes:891993755786293298>'
        self.no = '<:no:891993740116381718>'
        self.loading = '<a:Loading:892010799994929192>'


class Logs:
    def __init__(self):
        self.cmds: int = 889112702146986024
        self.cmd_errs: int = 889115230355996703
        self.event_errs: int = 888368018915209236
        self.add_remove: int = 889116736077570068


class Config:
    def __init__(self):
        self.emojis = Emojis()
        self.logs = Logs()
        self.prefixes = ['<', '?']
        self.status = 'my dms'
        self.owners = [321750582912221184, 558861606063308822]
        self.client_secret = os.environ.get('CLIENT_SECRET')
