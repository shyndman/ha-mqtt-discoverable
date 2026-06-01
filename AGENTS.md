# AGENTS

## Media player capability signaling

`ha_mqtt_discoverable.media_player` is a device-side library for many different media-player implementations, not one fixed player.

For optional media-player features, capability is signaled by the published discovery topic contract:

- if an optional topic is present, control-side integrations may treat that feature as supported
- if an optional topic is absent, control-side integrations should treat that feature as unsupported

Keep topic emission and capability in lockstep. Do not advertise optional discovery topics unless the device implementation actually supports the matching feature.

For mute, shuffle, repeat, and similar paired state/command capabilities, emit both the command topic and the corresponding state topic only when the matching device callback exists.
