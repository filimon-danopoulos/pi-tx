"""Tests for the value_store module."""

import pytest
import os
import json
import tempfile
from pi_tx.domain.value_store import ValueStore


class TestValueStore:
    
    def test_basic_functionality(self):
        """Test basic value storage and retrieval."""
        # Use temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"reverse": {}, "channel_types": {}}, f)
            config_path = f.name
        
        try:
            store = ValueStore(size=10, config_path=config_path)
            
            # Test setting and getting values
            store.set_value(1, 0.5)
            assert store.get_raw_value(1) == 0.5
            assert store.get_value(1) == 0.5
            
            # Test multiple values
            store.set_many({2: 0.8, 3: -0.3})
            assert store.get_raw_value(2) == 0.8
            assert store.get_raw_value(3) == -0.3
            
        finally:
            os.unlink(config_path)
    
    def test_reversing_unipolar(self):
        """Test reversing for unipolar channels."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "reverse": {"1": True}, 
                "channel_types": {"1": "unipolar"}
            }, f)
            config_path = f.name
        
        try:
            store = ValueStore(size=10, config_path=config_path)
            
            # Test unipolar reversing (1.0 - value)
            store.set_value(1, 0.3)
            assert store.get_raw_value(1) == 0.3
            assert store.get_value(1) == 0.7  # 1.0 - 0.3
            
        finally:
            os.unlink(config_path)
    
    def test_reversing_bipolar(self):
        """Test reversing for bipolar channels."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "reverse": {"2": True}, 
                "channel_types": {"2": "bipolar"}
            }, f)
            config_path = f.name
        
        try:
            store = ValueStore(size=10, config_path=config_path)
            
            # Test bipolar reversing (-value)
            store.set_value(2, 0.6)
            assert store.get_raw_value(2) == 0.6
            assert store.get_value(2) == -0.6
            
            store.set_value(2, -0.4)
            assert store.get_raw_value(2) == -0.4
            assert store.get_value(2) == 0.4
            
        finally:
            os.unlink(config_path)
    
    def test_dynamic_configuration(self):
        """Test runtime configuration changes."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"reverse": {}, "channel_types": {}}, f)
            config_path = f.name
        
        try:
            store = ValueStore(size=10, config_path=config_path)
            
            # Set initial value
            store.set_value(3, 0.8)
            assert store.get_value(3) == 0.8
            
            # Enable reversing for channel 3
            store.set_reverse(3, True)
            assert abs(store.get_value(3) - 0.2) < 1e-10  # 1.0 - 0.8 (default unipolar)
            
            # Change to bipolar
            store.set_channel_type(3, "bipolar")
            assert store.get_value(3) == -0.8  # -0.8 (bipolar)
            
            # Disable reversing
            store.set_reverse(3, False)
            assert store.get_value(3) == 0.8  # back to original
            
        finally:
            os.unlink(config_path)
    
    def test_snapshots(self):
        """Test snapshot functionality."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "reverse": {"1": True}, 
                "channel_types": {"1": "unipolar"}
            }, f)
            config_path = f.name
        
        try:
            store = ValueStore(size=5, config_path=config_path)
            
            # Set some values
            store.set_many({1: 0.3, 2: 0.7, 3: -0.5})
            
            raw_snap = store.raw_snapshot()
            processed_snap = store.snapshot()
            
            # Raw snapshot should match input
            assert raw_snap[0] == 0.3  # channel 1
            assert raw_snap[1] == 0.7  # channel 2
            assert raw_snap[2] == -0.5  # channel 3
            
            # Processed snapshot should have reversing applied
            assert processed_snap[0] == 0.7  # 1.0 - 0.3 (reversed unipolar)
            assert processed_snap[1] == 0.7  # no change (not reversed)
            assert processed_snap[2] == -0.5  # no change (not reversed)
            
        finally:
            os.unlink(config_path)
    
    def test_configuration_persistence(self):
        """Test saving and loading configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"reverse": {}, "channel_types": {}}, f)
            config_path = f.name
        
        try:
            # Create store and configure it
            store1 = ValueStore(size=10, config_path=config_path)
            store1.set_reverse(1, True)
            store1.set_reverse(3, True)
            store1.set_channel_type(1, "bipolar")
            store1.save_configuration()
            
            # Create new store with same config file
            store2 = ValueStore(size=10, config_path=config_path)
            
            # Test that configuration was loaded
            assert store2.is_reversed(1) == True
            assert store2.is_reversed(2) == False
            assert store2.is_reversed(3) == True
            assert store2.get_channel_type(1) == "bipolar"
            assert store2.get_channel_type(2) == "unipolar"  # default
            
        finally:
            os.unlink(config_path)


if __name__ == "__main__":
    # Run a simple test if executed directly
    test = TestValueStore()
    test.test_basic_functionality()
    test.test_reversing_unipolar()
    test.test_reversing_bipolar()
    test.test_dynamic_configuration()
    test.test_snapshots()
    test.test_configuration_persistence()
    print("All tests passed!")
