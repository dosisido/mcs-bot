# MineCraft Server Bot for discord

This project was created to add some custom features for a two-week Minecraft phase for my friends and me.

---

## Features
- Relays Minecraft chat and important server events into a Discord log channel.
- Welcomes new or existing Discord members, creates a temporary private channel, and whitelists them via RCON after they confirm their Minecraft username. The bot stores the Discord → Minecraft mapping under `/data/discord_mappings.json`.
- Listens to a configured command channel; every message is executed against the Minecraft server through RCON and the response is posted back in Discord.
- Security and RBAC handled via Discord's role feature

## Requirements
- Designed to run alongside [itzg/docker-minecraft-server](https://github.com/itzg/docker-minecraft-server); adapt as needed for other server setups.
- In the Discord Developer Portal enable:
  - **Server Members Intent**
  - **Message Content Intent**
- Grant the bot permissions in your guild to Manage Channels, Manage Roles, Send Messages, and Read Message History.
- The Minecraft server must load the bundled `log4j_bridge.xml` via `-Dlog4j.configurationFile=/log4j_conf/log4j_bridge.xml` so its console output is forwarded to the bot.

## Environment variables
- `DISCORD_BOT_TOKEN` (required): Discord bot token.
- `DISCORD_CHANNEL_ID` (required): Channel ID for Minecraft log relay.
- `DISCORD_GUILD_ID` (required): Guild where verification and role management happen.
- `DISCORD_VERIFIED_ROLE_ID` (required): Role granted after successful whitelist verification.
- `DISCORD_COMMAND_CHANNEL_ID` (required): Channel whose messages are executed as RCON commands.
- `RCON_HOST`, `RCON_PORT`, `RCON_PASSWORD` (required): Connection info for the Minecraft server’s RCON endpoint.
- `WHITELIST_STORE_PATH` (optional): Where to write the Discord ↔ Minecraft mapping JSON (defaults to `/data/discord_mappings.json`).

The bot stores data at `/data`, mount the folder as container to make the changes survive container restarts.

## Example docker compose
```yaml
services:
  server:
    image: itzg/minecraft-server:latest
    pull_policy: daily
    ports:
      - "25565:25565"
    environment:
      JVM_OPTS: "-XX:+UseContainerSupport -Dlog4j.configurationFile=/log4j_conf/log4j_bridge.xml"
      ENABLE_RCON: "true"
      RCON_PASSWORD: "${RCON_PASSWORD}"
      RCON_PORT: "25575"
    volumes:
      - ./mcs-data:/data
      - log4j_conf:/log4j_conf

  mcs-bot:
    image: dosisido/mcs-bot
    environment:
      DISCORD_BOT_TOKEN: "${DISCORD_BOT_TOKEN}"
      DISCORD_CHANNEL_ID: "${DISCORD_CHANNEL_ID}"
      DISCORD_GUILD_ID: "${DISCORD_GUILD_ID}"
      DISCORD_VERIFIED_ROLE_ID: "${DISCORD_VERIFIED_ROLE_ID}"
      DISCORD_COMMAND_CHANNEL_ID: "${DISCORD_COMMAND_CHANNEL_ID}"
      RCON_HOST: "server"
      RCON_PORT: "25575"
      RCON_PASSWORD: "${RCON_PASSWORD}"
    volumes:
      - log4j_conf:/log4j_conf
      - ./bot-data:/data

volumes:
  log4j_conf:
```

## Contributing
Issues and pull requests are welcome. If something does not work as expected, open an issue on github describing the desired behavior.

[Github Repository](https://github.com/dosisido/mcs-bot)