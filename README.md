# MineCraft Server Bot for discord

This project was created to add some custom features for a two-week Minecraft phase for my friends and me.

---

## How to use
This project is designed to be used with [itzg/docker-minecraft-server](https://github.com/itzg/docker-minecraft-server), but it can also be used with a manual installation (left to the reader).

It requires two environment variables:
- DISCORD_BOT_TOKEN: self-explanatory
- DISCORD_CHANNEL_ID: the ID of the channel where the bot will send messages. To get this, enable Developer Mode in your account settings, then right-click the channel and copy its ID from the bottom.

The container inside the compose **must** be called `mcs-bot` and the Minecraft server must have access to the `/log4j_conf` folder inside this container, which contains the `log4j_bridge.xml` configuration file. The server must also be started with the following command-line argument: 
`-Dlog4j.configurationFile=/log4j_conf/log4j_bridge.xml`

This is a sample docker compose:
```yaml
services:
  server:
    image: itzg/minecraft-server:latest
    pull_policy: daily
    ports:
      - "25565:25565"
    environment:
      JVM_OPTS: "-XX:+UseContainerSupport -Dlog4j.configurationFile=/log4j_conf/log4j_bridge.xml"
    volumes:
      - ./mcs-data:/data
      - log4j_conf:/log4j_conf
  
  mcs-bot:
    image: dosisido/mcs-bot
    environment:
      DISCORD_BOT_TOKEN: "${DISCORD_BOT_TOKEN}"
      DISCORD_CHANNEL_ID: "${DISCORD_CHANNEL_ID}"
    depends_on:
      - server
    volumes:
      - log4j_conf:/log4j_conf

volumes:
  log4j_conf:
```

## Contributing
Issues and pull requests are welcome. If something does not work as expected, open an issue on github describing the desired behavior.

[Github Repository](https://github.com/dosisido/mcs-bot)