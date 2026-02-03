"""
Church Stream Sync - Automatic synchronization system for live streaming.

This system automatically manages two computers used in church live streaming:
- OBS PC: Main computer running OBS Studio (operator)
- Audio PC: Secondary computer connected to the audio mixer via USB

Features:
- Turns on the Audio PC when the OBS PC logs in (using Wake-on-LAN)
- Turns off the Audio PC when the OBS PC shuts down (using remote shutdown)
- Provides visual UI feedback with progress tracking
"""

__version__ = "1.0.0"
__author__ = "Filipe Pereira"
__description__ = "Automatic synchronization system OBS PC <-> Audio PC"
