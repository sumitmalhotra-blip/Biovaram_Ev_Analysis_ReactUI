"""
Channel Configuration Utility for FCS Analysis.

This module provides centralized channel mapping configuration for different
flow cytometry instruments. It reads from config/channel_config.json and
provides methods to detect and map FSC/SSC channels.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from loguru import logger


class ChannelConfig:
    """
    Channel configuration manager for flow cytometry data.
    
    Provides automatic detection and mapping of FSC/SSC channels
    based on instrument configuration.
    """
    
    _instance = None
    _config = None
    _config_path = Path(__file__).parent.parent.parent / "config" / "channel_config.json"
    
    def __new__(cls):
        """Singleton pattern to ensure consistent configuration."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self) -> None:
        """Load channel configuration from JSON file."""
        try:
            if self._config_path.exists():
                with open(self._config_path, 'r') as f:
                    self._config = json.load(f)
                logger.info(f"✓ Loaded channel config from {self._config_path}")
            else:
                logger.warning(f"Channel config not found at {self._config_path}, using defaults")
                self._config = self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading channel config: {e}")
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Return default channel configuration."""
        return {
            "active_instrument": "custom",
            "instruments": {
                "custom": {
                    "channel_mappings": {
                        "fsc": {"channel_names": ["FSC-A", "FSC-H", "VFSC-A", "Channel_1"]},
                        "ssc": {"channel_names": ["SSC-A", "SSC-H", "VSSC1-A", "Channel_2"]}
                    },
                    "preferred_scatter_channels": {
                        "for_size_analysis": {"fsc": "FSC-A", "ssc": "SSC-A"},
                        "for_scatter_plot": {"fsc": "FSC-A", "ssc": "SSC-A"}
                    }
                }
            },
            "baseline_keywords": ["ISO", "Isotype", "isotype", "control", "blank", "water"]
        }
    
    def reload_config(self) -> None:
        """Reload configuration from file."""
        self._load_config()
    
    @property
    def active_instrument(self) -> str:
        """Get the currently active instrument name."""
        return self._config.get("active_instrument", "custom")
    
    @property
    def instrument_config(self) -> Dict:
        """Get the configuration for the active instrument."""
        instruments = self._config.get("instruments", {})
        return instruments.get(self.active_instrument, instruments.get("custom", {}))
    
    def get_fsc_channel_names(self) -> List[str]:
        """Get list of possible FSC channel names for the active instrument."""
        mappings = self.instrument_config.get("channel_mappings", {})
        fsc_config = mappings.get("fsc", {})
        return fsc_config.get("channel_names", ["FSC-A", "FSC-H"])
    
    def get_ssc_channel_names(self) -> List[str]:
        """Get list of possible SSC channel names for the active instrument."""
        mappings = self.instrument_config.get("channel_mappings", {})
        ssc_config = mappings.get("ssc", {})
        return ssc_config.get("channel_names", ["SSC-A", "SSC-H"])
    
    def get_preferred_channels(self, purpose: str = "for_size_analysis") -> Tuple[str, str]:
        """
        Get preferred FSC/SSC channel names for a specific purpose.
        
        Args:
            purpose: Either "for_size_analysis" or "for_scatter_plot"
        
        Returns:
            Tuple of (fsc_channel, ssc_channel)
        """
        prefs = self.instrument_config.get("preferred_scatter_channels", {})
        purpose_prefs = prefs.get(purpose, prefs.get("for_size_analysis", {}))
        return (
            purpose_prefs.get("fsc", "FSC-A"),
            purpose_prefs.get("ssc", "SSC-A")
        )
    
    def detect_fsc_channel(self, available_channels: List[str]) -> Optional[str]:
        """
        Detect FSC channel from available channels.
        
        Args:
            available_channels: List of channel names in the FCS file
        
        Returns:
            The detected FSC channel name, or None if not found
        """
        # First, check preferred channel
        preferred_fsc, _ = self.get_preferred_channels()
        if preferred_fsc in available_channels:
            logger.info(f"✓ Using preferred FSC channel: {preferred_fsc}")
            return preferred_fsc
        
        # Then, try all possible FSC channel names
        for channel in self.get_fsc_channel_names():
            if channel in available_channels:
                logger.info(f"✓ Detected FSC channel: {channel}")
                return channel
        
        # Try case-insensitive matching
        available_lower = {ch.lower(): ch for ch in available_channels}
        for channel in self.get_fsc_channel_names():
            if channel.lower() in available_lower:
                detected = available_lower[channel.lower()]
                logger.info(f"✓ Detected FSC channel (case-insensitive): {detected}")
                return detected
        
        logger.warning(f"⚠ FSC channel not found. Available: {available_channels[:10]}...")
        return None
    
    def detect_ssc_channel(self, available_channels: List[str]) -> Optional[str]:
        """
        Detect SSC channel from available channels.
        
        Args:
            available_channels: List of channel names in the FCS file
        
        Returns:
            The detected SSC channel name, or None if not found
        """
        # First, check preferred channel
        _, preferred_ssc = self.get_preferred_channels()
        if preferred_ssc in available_channels:
            logger.info(f"✓ Using preferred SSC channel: {preferred_ssc}")
            return preferred_ssc
        
        # Then, try all possible SSC channel names
        for channel in self.get_ssc_channel_names():
            if channel in available_channels:
                logger.info(f"✓ Detected SSC channel: {channel}")
                return channel
        
        # Try case-insensitive matching
        available_lower = {ch.lower(): ch for ch in available_channels}
        for channel in self.get_ssc_channel_names():
            if channel.lower() in available_lower:
                detected = available_lower[channel.lower()]
                logger.info(f"✓ Detected SSC channel (case-insensitive): {detected}")
                return detected
        
        logger.warning(f"⚠ SSC channel not found. Available: {available_channels[:10]}...")
        return None
    
    def detect_scatter_channels(self, available_channels: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect both FSC and SSC channels from available channels.
        
        Args:
            available_channels: List of channel names in the FCS file
        
        Returns:
            Tuple of (fsc_channel, ssc_channel), either may be None if not found
        """
        fsc = self.detect_fsc_channel(available_channels)
        ssc = self.detect_ssc_channel(available_channels)
        return (fsc, ssc)
    
    def is_baseline_sample(self, filename: str) -> bool:
        """
        Check if a sample is a baseline/control based on filename.
        
        Args:
            filename: The FCS filename
        
        Returns:
            True if this appears to be a baseline/control sample
        """
        keywords = self._config.get("baseline_keywords", ["ISO", "isotype", "control"])
        return any(kw in filename for kw in keywords)
    
    def get_qc_thresholds(self) -> Dict:
        """Get QC thresholds from configuration."""
        return self._config.get("qc_thresholds", {
            "min_events": 1000,
            "max_cv_percent": 50,
            "min_median_fsc": 100,
            "max_relative_error_percent": 30
        })
    
    def list_instruments(self) -> List[str]:
        """List all available instrument configurations."""
        return list(self._config.get("instruments", {}).keys())
    
    def set_active_instrument(self, instrument_name: str) -> bool:
        """
        Set the active instrument.
        
        Args:
            instrument_name: Name of the instrument to activate
        
        Returns:
            True if successful, False if instrument not found
        """
        if instrument_name in self._config.get("instruments", {}):
            self._config["active_instrument"] = instrument_name
            logger.info(f"✓ Active instrument set to: {instrument_name}")
            return True
        else:
            logger.warning(f"⚠ Instrument '{instrument_name}' not found")
            return False
    
    def save_config(self) -> bool:
        """Save current configuration to file."""
        try:
            with open(self._config_path, 'w') as f:
                json.dump(self._config, f, indent=2)
            logger.info(f"✓ Saved channel config to {self._config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving channel config: {e}")
            return False
    
    def add_custom_channel_mapping(
        self,
        fsc_channel: str,
        ssc_channel: str,
        instrument_name: str = "custom"
    ) -> None:
        """
        Add custom FSC/SSC channel mapping.
        
        Args:
            fsc_channel: The FSC channel name in your FCS files
            ssc_channel: The SSC channel name in your FCS files
            instrument_name: Instrument configuration to update
        """
        if instrument_name not in self._config.get("instruments", {}):
            self._config.setdefault("instruments", {})[instrument_name] = {
                "channel_mappings": {"fsc": {"channel_names": []}, "ssc": {"channel_names": []}},
                "preferred_scatter_channels": {}
            }
        
        inst = self._config["instruments"][instrument_name]
        
        # Add to channel names if not present
        fsc_names = inst["channel_mappings"]["fsc"]["channel_names"]
        if fsc_channel not in fsc_names:
            fsc_names.insert(0, fsc_channel)
        
        ssc_names = inst["channel_mappings"]["ssc"]["channel_names"]
        if ssc_channel not in ssc_names:
            ssc_names.insert(0, ssc_channel)
        
        # Set as preferred
        inst["preferred_scatter_channels"] = {
            "for_size_analysis": {"fsc": fsc_channel, "ssc": ssc_channel},
            "for_scatter_plot": {"fsc": fsc_channel, "ssc": ssc_channel}
        }
        
        # Set as active instrument
        self._config["active_instrument"] = instrument_name
        
        logger.info(f"✓ Added channel mapping: FSC={fsc_channel}, SSC={ssc_channel}")


# Convenience function to get the singleton instance
def get_channel_config() -> ChannelConfig:
    """Get the global channel configuration instance."""
    return ChannelConfig()
