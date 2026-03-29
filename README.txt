# Kelly's Creepy Death Digger Machine v1.1

Kelly's Creepy Death Digger Machine is a standalone Windows desktop application designed to search multiple obituary databases simultaneously.

## Features
- Multi-source search (Legacy.com, Tributes.com, SSDI, FindAGrave, Google News)
- Secure Credentials Manager (encrypted storage)
- Local SQLite database for indexing and caching
- Export to Excel (.xlsx) or Append to existing spreadsheets

## Installation & First Launch
1. Run `KellysCreepyDeathDiggerMachine.exe`.
2. On first launch, go to **Settings > Sources & Credentials**.
3. Enter your FamilySearch or FindAGrave credentials to enable those sources (optional).
4. Click **Save All Settings**.

## Requirements
- Windows 10/11
- No Python installation required (standalone EXE)

## Developer Notes
Built with Python 3.11 and PyQt6.
Data is stored locally in `%APPDATA%\KellysCreepyDeathDiggerMachine\`.
