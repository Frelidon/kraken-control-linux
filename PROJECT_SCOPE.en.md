# Project scope - Kraken Control by Frelidon 2.9.6

## Purpose

Kraken Control is a focused Linux application for supported NZXT Kraken liquid coolers. Keeping a strict boundary reduces risk, simplifies testing and prevents conflicts with firmware, motherboard utilities or GPU drivers.

## Included in Kraken Control

- coolant temperature and device status of the supported Kraken
- Kraken pump
- radiator fans when reported or controlled through the Kraken itself
- Kraken LCD and static LCD content
- separate NZXT 2023 RGB Controller
- diagnostics limited to supported Kraken hardware

## Not included in Kraken Control

- motherboard headers such as CPU_FAN, SYS_FAN or CHA_FAN
- additional chassis fans not controlled through the Kraken
- GPU fans and AMD graphics controls
- general sensor, overclocking or system-tuning features
- automatic changes to firmware or motherboard fan profiles

## Modular future

Other hardware areas should be developed as separate applications with their own safety boundaries. A future shared front end may launch those tools or combine status information without removing the clear responsibility of each individual program.

## Version 2.8 clarification

CPU temperature may be read only to safely assist the supported Kraken cooling device. General motherboard, GPU and system tuning remain out of scope.
