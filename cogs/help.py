import discord
from discord.ext import commands
from discord.ui import Select, View, Button
from utils.constants import StriveConstants
from utils.embeds import HelpCenterEmbed
from utils.utils import StriveContext
from typing import Optional

constants = StriveConstants()

EXCLUDED_COMMANDS = ['jishaku', 
                     'debug', 
                     'addowner', 
                     'removeowner', 
                     'sync', 
                     'checkguild', 
                     'showowners', 
                     'blacklist', 
                     'unblacklist']

class HelpView(View):
    def __init__(self, cog, timeout: Optional[float] = 180):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.current_page = 0
        self.add_item(self.CategorySelect(cog))
        
    class CategorySelect(Select):
        def __init__(self, cog):
            self.cog = cog
            options = [
                discord.SelectOption(
                    label=cat,
                    description=f"View {cat} commands",
                    emoji=cog.category_emojis.get(cat, "")
                )
                for cat in cog.categories
            ]
            super().__init__(placeholder="Select a category", options=options)

        async def callback(self, interaction: discord.Interaction):
            category = self.values[0]
            embed = await self.cog.create_category_embed(category)
            await interaction.response.edit_message(embed=embed, view=self.view)

    @discord.ui.button(label="Home", style=discord.ButtonStyle.blurple, custom_id="home")
    async def home_button(self, interaction: discord.Interaction, button: Button):
        embed = await self.cog.create_home_embed()
        await interaction.response.edit_message(embed=embed, view=self)

class HelpCommandsCog(commands.Cog):
    def __init__(self, strive):
        self.strive = strive
        self.categories = self.get_command_categories()
        self.category_emojis = {
            "General": "<:Development:1327195371771789324>",
            "Moderation": "<:banned:1326788110305988659>",
            "Other": "<:settings:1327195042602942508>",
        }

    async def create_home_embed(self) -> discord.Embed:
        embed = HelpCenterEmbed(
            description="Welcome to Strive! Use the dropdown menu below to explore command categories.\n\n"
                       "**Quick Tips:**\n"
                       "• Select a category to view its commands\n"
                       "• Click on command links to use them\n"
                       "• Use the Home button to return to this menu",
            color=constants.strive_embed_color_setup()
        )
        
        # Add category overview
        for category in self.categories:
            cmd_count = len([cmd for cmd in self.strive.commands 
                           if cmd.extras.get('category', 'General') == category
                           and cmd.qualified_name not in EXCLUDED_COMMANDS])
            embed.add_field(
                name=f"{self.category_emojis.get(category, '')} {category}",
                value=f"`{cmd_count} commands`",
                inline=True
            )
        
        return embed

    async def create_category_embed(self, category: str) -> discord.Embed:
        embed = discord.Embed(
            title=f"{self.category_emojis.get(category, '')} {category} Commands",
            color=constants.strive_embed_color_setup()
        )
        
        commands_in_category = [cmd for cmd in self.strive.commands 
                              if cmd.extras.get('category', 'General') == category
                              and cmd.qualified_name not in EXCLUDED_COMMANDS]
        
        slash_commands = {cmd.name: cmd for cmd in self.strive.tree.get_commands()}
        
        for command in commands_in_category:
            name = command.qualified_name
            desc = command.description or 'No description provided.'
            
            slash_cmd = slash_commands.get(name)
            if slash_cmd and hasattr(slash_cmd, 'id') and slash_cmd.id:
                name = f"</{name}:{slash_cmd.id}>"
            else:
                name = f"/{name}"
                
            embed.add_field(
                name=name,
                value=desc,
                inline=False
            )
            
        return embed

    @commands.hybrid_command(description="Browse through bot commands and learn how to use them.", with_app_command=True, extras={"category": "Help"})
    async def help(self, ctx: StriveContext):
        await ctx.defer(ephemeral=False)
        
        embed = await self.create_home_embed()
        view = HelpView(self)
        
        await ctx.send(embed=embed, view=view)

    def get_command_categories(self) -> list:
        categories = set()
        for command in self.strive.commands:
            if isinstance(command, commands.HybridCommand) or isinstance(command, commands.Command):
                category = command.extras.get('category', 'General')
                categories.add(category)
        return sorted(categories)

async def setup(strive):
    await strive.add_cog(HelpCommandsCog(strive))