import sys
import platform
import importlib.util
from dataclasses import dataclass

class RuntimeInfo:
    def _check_import(self, module: str) -> bool:
        try:
            __import__(module)
            return True
        except ImportError:
            return False
     
    @classmethod
    def is_linux(cls) -> bool:
        return sys.platform.startswith("linux")
     
    @classmethod
    def is_windows(cls) -> bool:
        return sys.platform.startswith("win")

    @classmethod
    def is_raspberry_pi(cls) -> bool:
        if not cls.is_linux():
            return False
        try:
            with open("/proc/cpuinfo", "r") as f:
                return "Raspberry Pi" in f.read()
        except Exception:
            return False

    @classmethod
    def has_ws281x(cls) -> bool:
        return cls.has_module("rpi_ws281x")   
      

    @classmethod
    def has_gpio(cls) -> bool:
        return cls.has_module("RPi.GPIO")   

    @classmethod
    def has_evdev(cls) -> bool:
        return cls.has_module("evdev")   
            
    @classmethod
    def has_module(cls, module_name: str) -> bool:
        try:
            return importlib.util.find_spec(module_name) is not None
        except Exception:
            return False
        