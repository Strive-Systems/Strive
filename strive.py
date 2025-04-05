import discord
import os
import requests
import asyncio
import sentry_sdk
from datetime import datetime
from discord.ext import commands
from utils.constants import StriveConstants, afks, prefixes
from utils.utils import get_prefix, StriveContext
from cogwatch import watch

# We use constants.py to specify things like the mongo db connnection, prefix
# and default embed color.

constants = StriveConstants()


class Strive(commands.AutoShardedBot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.token = None
        self.start_time = datetime.now()
        self.beta_guilds = [1338770040820072523]  # Strive Support

        self.error = "<:strivefail:1338900416972193902>"
        self.success = "<:strivesuccess:1338900384932036618>"
        self.loading = "<a:loading:1338811352692817920>"
        self.warning = "<:striveWarning:1338900771823030373>"
        self.base_color = 0x66D8FF
        self.context = StriveContext

    async def get_context(self, message, *, cls=StriveContext):
        return await super().get_context(message, cls=cls)

    @watch(path="cogs", preload=False)
    async def on_ready(self):
        strive.prefixes = {}

        guilds = prefixes.find()
        async for guild in guilds:
            strive.prefixes[guild.get("guild_id")] = guild.get("prefix")

        strive.afk_users = []

        all_afks = afks.find({})
        async for afk in all_afks:
            afk_doc = {"user_id": afk.get("user_id"), "guild_id": afk.get("guild_id")}
            strive.afk_users.append(afk_doc)

        if constants.strive_environment_type() == "Development":
            for guild in strive.guilds:

                id = guild.id
                owner = guild.get_member(guild.owner_id)
                is_dev_guild = id in self.beta_guilds
                channel = strive.get_guild(self.beta_guilds[0]).get_channel(
                    1338806026094247968
                )

                # Check if owner is None

                if owner is None:
                    owner_info = "Owner not found"
                else:
                    owner_info = f"{owner}({owner.id})"

                embed = discord.Embed(
                    title="Beta bot added to a guild",
                    description=f"**NAME:** `{guild.name}`\n**ID:** `{id}`\n**OWNER:** `{owner_info}`\n**IS_DEV_GUILD:** `{is_dev_guild}`",
                )

                if not is_dev_guild:
                    await guild.leave()
                    await channel.send(embed=embed)

        else:

            guild_count = len(strive.guilds)
            user_count = sum(
                guild.member_count or 0 for guild in strive.guilds
            )  # Default to 0 if None

            await strive.change_presence(
                activity=discord.Activity(
                    name=f"{guild_count} Guilds • {user_count:,} Users • /help",
                    type=discord.ActivityType.watching,
                )
            )

        print(
            f"{strive.user.name} is ready!"
        )  # with {guild_count} guilds and {user_count:,} users.

    # Use bypassed users from the constants class instead of hardcoding them
    # The constants.py file will get the IDs from MongoDb allowing bot owners
    # to remove and add users.

    async def is_owner(self, user: discord.User):
        await constants.fetch_bypassed_users()
        return user.id in constants.bypassed_users

    # Sets up the cogs for strive. This will cycle thru the cogs folder and
    # load each file with the .py file extenstion.

    async def setup_hook(self) -> None:
        for root, _, files in os.walk("./cogs"):
            for file in files:
                if file.endswith(".py"):
                    cog_path = os.path.relpath(os.path.join(root, file), "./cogs")
                    cog_module = cog_path.replace(os.sep, ".")[:-3]

                    await strive.load_extension(f"cogs.{cog_module}")

        print("All cogs loaded successfully!")

    async def refresh_blacklist_periodically(self):
        while True:
            await self.constants.refresh_blacklists()
            await asyncio.sleep(3600)


# Sets the bot's intents. This uses the members intent, default intents, and message_content
# intent. We will call intents later inorder to start Strive.

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


# Intializes strive Bot and loads the prefix, intents, and other important things for discord.

strive = Strive(
    command_prefix=get_prefix,
    intents=intents,
    chunk_guilds_at_startup=False,
    help_command=None,
    allowed_mentions=discord.AllowedMentions(
        replied_user=True, everyone=True, roles=True
    ),
    cls=StriveContext,
)


# Before invoking any command, check blacklist.


@strive.before_invoke
async def before_invoke(ctx):

    # Skip check if the user is in the bypass list

    if ctx.author.id in constants.bypassed_users:
        return

    # Run the blacklist check

    await global_blacklist_check(ctx)


async def global_blacklist_check(ctx):

    # Fetch blacklist if not already fetched or periodically

    await constants.fetch_blacklisted_users()
    await constants.fetch_blacklisted_guilds()

    # Check if the user is blacklisted

    if ctx.author.id in constants.blacklists and ctx.command.name != "unblacklist":

        em = discord.Embed(
            title="",
            description=f"{strive.warning} **Blacklisted User** \n\n> You are blacklisted from Strive - Please appeal within our [Support Server](https://discord.gg/rkRrRfRTwg) or email `support@strivebot.xyz`!",
            color=constants.strive_embed_color_setup(),
        )

        await ctx.send(embed=em)

        raise commands.CheckFailure("You are blacklisted from using Strive.")

    # Check if the guild is blacklisted

    if ctx.guild and ctx.guild.id in constants.blacklists and ctx.command.name != "unblacklist":
        
        em = discord.Embed(
            title="",
            description="<:warning:1335369524291178506> **Blacklisted Guild** \n\n> This server is blacklisted from Strive - Please appeal within our [Support Server](https://discord.gg/rkRrRfRTwg) or email `support@strivebot.xyz`!",
            color=constants.strive_embed_color_setup(),
        )
        
        await ctx.send(embed=em)
        
        raise commands.CheckFailure("This guild is blacklisted from using Strive.")

    # Prevent the command from being run in DMs

    if ctx.guild is None:
        raise commands.NoPrivateMessage(
            "This command cannot be used in private messages."
        )

    return True


def run():

    # Sets up sentry for advanced error reporting.
    # We use Nexure's sentry account.

    sentry_sdk.init(
        dsn=constants.sentry_dsn_setup(),
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

    strive.run(constants.strive_token_setup())


if __name__ == "__main__":
    run()
