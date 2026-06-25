<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Changelog](#changelog)
  - [0.15.0](#0150)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Changelog

## 1.1.0

- Reject media-player ON/OFF command payloads that are not exactly `ON`/`OFF`, logging a warning instead of silently treating them as off
- Dispatch MQTT command callbacks concurrently as tracked tasks so a slow callback on one topic no longer blocks other entities' callbacks; in-flight callbacks are drained on shutdown (drops the implicit in-order/no-overlap delivery guarantee)

## 0.15.0

- Removed `thelogrus` from the dependency list
