import discord
from discord.ext import commands
from utils.embeds import PingCommandEmbed

class PingPaginationView(discord.ui.View):
    def __init__(self, strive: commands.Bot, latency, database_latency, uptime, shard_info):
        super().__init__()
        self.strive = strive
        self.latency = latency
        self.database_latency = database_latency
        self.uptime = uptime
        self.shard_info = shard_info
        self.page = 0
        self.max_page = (len(shard_info) // 5) + 1



    async def update_message(self, interaction: discord.Interaction):
        
        
        embed = PingCommandEmbed.create_ping_embed(
            self.latency, self.database_latency, self.uptime, self.shard_info, self.page
        )
        
        self.update_buttons()
        
        await interaction.response.edit_message(embed=embed, view=self)


    def update_buttons(self):
        self.prev_button.disabled = self.page == 0
        self.next_button.disabled = self.page >= self.max_page
        self.page_button.label = "Network" if self.page == 0 else "Shards"
        self.page_button.emoji = "<:settings:1327195042602942508>" if self.page == 0 else "<:clock:1334022552326111353>"


    @discord.ui.button(emoji="<:left:1332555046956826646>", style=discord.ButtonStyle.gray, disabled=True)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            self.next_button.disabled = False
            if self.page == 0:
                self.prev_button.disabled = True
            await self.update_message(interaction)


    @discord.ui.button(emoji="<:settings:1327195042602942508>", label="Network", style=discord.ButtonStyle.blurple, disabled=True)
    async def page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass


    @discord.ui.button(emoji="<:right:1332554985153626113>", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.max_page:
            self.page += 1
            self.prev_button.disabled = False
            if self.page == self.max_page:
                self.next_button.disabled = True
            await self.update_message(interaction)