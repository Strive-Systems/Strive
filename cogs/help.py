import discord
from discord.ext import commands
from discord.ui import Select, View
from utils.constants import StriveConstants
from utils.embeds import HelpCenterEmbed
from utils.utils import StriveContext
from typing import List, Set

constants = StriveConstants()

EXCLUDED_COMMANDS = [
    'jishaku', 'debug', 'addowner', 'removeowner', 
    'sync', 'checkguild', 'showowners', 'blacklist', 
    'unblacklist'
]

class HelpCommandsCog(commands.Cog):
    """A cog that handles the help command functionality with an interactive dropdown menu."""
    
    def __init__(self, strive):
        self.strive = strive
        self.categories = self.get_command_categories()

    @commands.hybrid_command(
        name="help",
        description="Provides information on the bot's commands and how to use them.",
        with_app_command=True,
        extras={"category": "Help"}
    )
    async def help(self, ctx: StriveContext) -> None:
        """Display an interactive help menu with categorized commands."""
        await ctx.defer(ephemeral=False)
        
        class HelpDropdown(Select):
            def __init__(self, categories: List[str], strive):
                self.strive = strive
                options = [
                    discord.SelectOption(
                        label=cat,
                        description=f"View {cat} commands",
                        emoji=None
                    )
                    for cat in categories
                ]
                super().__init__(
                    placeholder="Choose a command category...",
                    options=options,
                    min_values=1,
                    max_values=1
                )

            async def callback(self, interaction: discord.Interaction) -> None:
                selected_category = self.values[0]
                command_list = self.get_commands_in_category(selected_category)

                embed = discord.Embed(
                    title=f"{selected_category} Commands",
                    description=command_list or "No commands available in this category.",
                    color=constants.strive_embed_color_setup()
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)

            def get_commands_in_category(self, category: str) -> str:
                commands_in_category = [
                    cmd for cmd in self.strive.commands 
                    if cmd.extras.get('category', 'General') == category
                    and cmd.qualified_name not in EXCLUDED_COMMANDS
                ]
                
                slash_commands = {cmd.name: cmd for cmd in self.strive.tree.get_commands()}
                command_entries = []

                for command in commands_in_category:
                    command_name = command.qualified_name
                    command_description = command.description or 'No description provided.'
                    
                    slash_command = slash_commands.get(command_name)
                    
                    if slash_command and hasattr(slash_command, 'id') and slash_command.id:
                        command_entries.append(f"</{command_name}:{slash_command.id}> - {command_description}")
                    else:
                        command_entries.append(f"`/{command_name}` - {command_description}")

                return "\n".join(command_entries) if command_entries else "No commands available."
        
        view = View(timeout=180)
        view.add_item(HelpDropdown(self.categories, self.strive))

        embed = HelpCenterEmbed(
            description=(
                "Welcome to Strive's interactive help menu! Here's how to get started:\n\n"
                "1️⃣ Select a category from the dropdown menu below\n"
                "2️⃣ Browse through the available commands\n"
                "3️⃣ Click on any command to use it directly\n\n"
                "Need more help? Join our support server or contact our team!"
            )
        )
        
        await ctx.send(embed=embed, view=view)

    def get_command_categories(self) -> Set[str]:
        """Get all unique command categories."""
        return sorted({
            command.extras.get('category', 'General')
            for command in self.strive.commands
            if isinstance(command, (commands.HybridCommand, commands.Command))
        })

async def setup(strive):
    await strive.add_cog(HelpCommandsCog(strive))