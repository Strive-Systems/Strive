import discord
from discord.ext import commands
from utils.constants import guild_counters, reminder_counters, prefixes
import os
from dotenv import load_dotenv

async def get_next_case_id(guild_id):
    
    guild_case_number = await guild_counters.find_one_and_update(
        {"_id": str(guild_id)},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    
    return guild_case_number["seq"]


async def get_next_reminder_id(guild_id):
    
    guild_reminder_number = await reminder_counters.find_one_and_update(
        {"_id": str(guild_id)},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    
    return guild_reminder_number["seq"]


async def get_prefix(strive, message):
    guild_data = await prefixes.find_one({"guild_id": str(message.guild.id)})
    
    if guild_data:
        prefix = guild_data.get("prefix")
    else:
        load_dotenv()
        prefix = str(os.getenv('PREFIX'))
    
    return commands.when_mentioned_or(prefix)(strive, message)