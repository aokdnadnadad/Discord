import discord

# Embed colors per action type
COLORS = {
    "SLUR_DELETE": discord.Color.light_grey(),
    "PURGE":       discord.Color.yellow(),
    "WARN":        discord.Color.orange(),
    "AUTO_TIMEOUT": discord.Color.red(),
    "AUTO_KICK":   discord.Color.dark_red(),
    "CLEAR_WARNS": discord.Color.blurple(),
}


async def send_mod_log(
    guild: discord.Guild,
    action: str,
    target: discord.abc.User | None = None,
    moderator: discord.abc.User | None = None,
    details: str | None = None,
):
    """Send a mod-log embed to the #mod-log channel (if it exists)."""
    channel = discord.utils.get(guild.text_channels, name="mod-log")
    if channel is None:
        return

    embed = discord.Embed(
        title=action.replace("_", " ").title(),
        color=COLORS.get(action, discord.Color.default()),
        timestamp=discord.utils.utcnow(),
    )

    if target:
        embed.add_field(name="User", value=f"{target.mention} ({target})", inline=True)
    if moderator:
        embed.add_field(name="Moderator", value=f"{moderator.mention} ({moderator})", inline=True)
    else:
        embed.add_field(name="Moderator", value="Automod", inline=True)
    if details:
        embed.add_field(name="Details", value=details, inline=False)

    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        print(f"Missing permission to send to #mod-log in {guild.name}")
