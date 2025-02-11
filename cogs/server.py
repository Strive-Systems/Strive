import discord
from discord.ext import commands
import traceback
import sys
from utils.embeds import AutoModListWordsEmbed
from utils.constants import StriveConstants, welcomer
from utils.utils import StriveContext

constants = StriveConstants()

class ServerCog(commands.Cog):
    def __init__(self, strive):
        self.strive = strive

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle command errors and log them to console"""
        error = getattr(error, 'original', error)
        
        if isinstance(error, commands.CommandNotFound):
            return
            
        print('[WELCOMER] {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    @commands.Cog.listener("on_member_join")
    async def welcome_message(self, member: discord.Member):
        """Send a welcome message for a member which joins the server"""

        async for doc in welcomer.find({"guild_id": member.guild.id}):
            channel = self.strive.get_channel(doc.get('channel_id'))
            if channel:
                try:
                    message = doc.get('message', f"Welcome {member.mention} to {member.guild.name}!")
                    ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4])
                    message = message.format(
                        user=member,
                        guild=member.guild,
                        guild_count=len(member.guild.members),
                        guild_count_ordinal=ordinal(len(member.guild.members))
                    )
                    await channel.send(
                        content=message,
                        allowed_mentions=discord.AllowedMentions(
                            everyone=True,
                            users=True,
                            roles=True,
                            replied_user=False
                        )
                    )
                except discord.Forbidden:
                    continue

    @commands.group(
        name="welcome",
        usage="(subcommand) <args>",
        example="add #chat Hi {user.mention} <3",
        aliases=["welc"],
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_guild=True)
    async def welcome(self, ctx: StriveContext):
        """Set up welcome messages in one or multiple channels"""
        await ctx.send_help()

    @welcome.command(
        name="variables",
        usage="",
        example="",
        aliases=["vars"],
    )
    @commands.has_permissions(manage_guild=True)
    async def welcome_variables(self, ctx: StriveContext):
        """Shows all available variables for welcome messages"""
        variables = [
            "`{user.mention}` - Mentions the joining user",
            "`{user.id}` - The user ID",
            "`{user.avatar}` - The user's avatar URL",
            "`{guild.count}` - Shows the guild member count",
            "`{guild.count_ordinal}` - The member count with ordinal suffix (1st, 2nd, etc)",
            "`{guild.name}` - Guild name"
        ]

        embed.add_field(
            name="Information",
            value="```\nExample: !welcome add #chat Hi {user.mention}\nSyntax: (channel) (message)\n```",
        )
        
        embed = discord.Embed(
            title="Welcome Message Variables",
            description="\n".join(variables),
            color=constants.strive_embed_color_setup()
        )
        await ctx.send(embed=embed)

    @welcome.command(
        name="add",
        usage="(channel) (message)",
        example="#chat Hi {user.mention}",
        aliases=["create"],
    )
    @commands.has_permissions(manage_guild=True)
    async def welcome_add(self, ctx: StriveContext, channel: discord.TextChannel, *, message: str = None):
        """Add a welcome message for a channel"""

        try:
            await welcomer.insert_one({
                "guild_id": ctx.guild.id,
                "channel_id": channel.id,
                "message": message or f"Welcome {{user.mention}} to {ctx.guild.name}!"
            })
        except:
            await ctx.send_error(f"There is already a welcome message for {channel.mention}")
        else:
            await ctx.send_success(f"Created welcome message for {channel.mention}")

    @welcome.command(
        name="remove",
        usage="(channel)",
        example="#chat",
        aliases=["delete", "del", "rm"],
    )
    @commands.has_permissions(manage_guild=True)
    async def welcome_remove(self, ctx: StriveContext, channel: discord.TextChannel):
        """Remove a welcome message for a channel"""

        result = await welcomer.delete_one({
            "guild_id": ctx.guild.id,
            "channel_id": channel.id
        })
        
        if result.deleted_count:
            await ctx.send_success(f"Removed the welcome message for {channel.mention}")
        else:
            await ctx.send_error(f"There isn't a welcome message for {channel.mention}")

    @welcome.command(
        name="test",
        usage="",
        example="",
        aliases=["try"],
    )
    @commands.has_permissions(manage_guild=True)
    async def welcome_test(self, ctx: StriveContext):
        """Test the welcome message system"""
        
        welcomer_exists = await welcomer.find_one({"guild_id": ctx.guild.id})
        if not welcomer_exists:
            return await ctx.send_error("No welcome messages have been set up. Use `welcome add` first!")

        await self.welcome_message(ctx.author)
        await ctx.send_success("Welcome message test executed!")

    @welcome.command(
        name="list",
        aliases=["show", "all"],
    )
    @commands.has_permissions(manage_guild=True)
    async def welcome_list(self, ctx: StriveContext):
        """View all welcome channels"""

        channels = []
        async for doc in welcomer.find({"guild_id": ctx.guild.id}):
            channel = ctx.guild.get_channel(doc.get("channel_id"))
            if channel:
                channels.append(channel.mention)

        if not channels:
            return await ctx.send_error("No welcome channels have been set up")

        await ctx.paginate(
            discord.Embed(
                title="Welcome Channels",
                description=channels,
                color=constants.strive_embed_color_setup()
            )
        )

async def setup(strive):
    await strive.add_cog(ServerCog(strive))