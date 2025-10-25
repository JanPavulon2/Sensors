"""
Parameter system - Type definitions and parameter registry

Defines parameter types, validation, and metadata for all system parameters.
Parameters are loaded from config.yaml (zone_parameters, animation_base_parameters, additional_animation_parameters).
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, List, Any, Dict
from enums import ParamID
import yaml
from pathlib import Path
import json
from enum import Enum

def parse_param_id(value):
    if isinstance(value, ParamID):
        return value
    if isinstance(value, str):
        try:
            return ParamID[value]
        except KeyError:
            raise ValueError(f"Unknown ParamID: {value}")
    raise TypeError(f"Invalid type for ParamID: {type(value)}")


def parse_animation_id(value):
    if isinstance(value, AnimationID):
        return value
    if isinstance(value, str):
        try:
            return AnimationID[value]
        except KeyError:
            raise ValueError(f"Unknown AnimationID: {value}")
    raise TypeError(f"Invalid type for AnimationID: {type(value)}")

def to_json(obj):
    if isinstance(obj, Enum):
        return obj.name
    raise TypeError(f"Type {type(obj)} not serializable")

#json.dump(state, file, default=to_json)

class ParameterType(Enum):
    """Parameter value types with validation rules"""
    COLOR = auto()           # Color parameter (HUE or PRESET mode)
    PERCENTAGE = auto()      # 0-100% (displayed with %, stored as 0-100)
    RANGE_0_255 = auto()     # 0-255 integer range (legacy brightness)
    RANGE_CUSTOM = auto()    # Custom min/max range
    BOOLEAN = auto()         # True/False toggle

class AnimationID(Enum):
    BREATHE = auto()
    COLOR_FADE = auto()
    SNAKE = auto()
    COLOR_SNAKE = auto()

### MODELE KOONFIGURACYJNE
@dataclass
class ParameterConfig:
    id: ParamID
    type: ParameterType
    default: Any
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[int] = None
    wraps: bool = False
    unit: Optional[str] = None
    description: str = ""

@dataclass
class AnimationConfig:
    id: AnimationID
    tag: str
    display_name: str
    description: str
    parameters: List[ParamID]
###

### MODELE STANU
@dataclass
class ParameterState:
    id: ParamID
    value: Any
    
@dataclass
class AnimationState:
    id: AnimationID
    enabled: bool
    parameter_values: Dict[ParamID, Any]
### 
    
### MODELE POŁĄCZONE
@dataclass
class ParameterCombined:
    config: ParameterConfig
    state: ParameterState

@dataclass
class AnimationCombined:
    config: AnimationConfig
    state: AnimationState
    parameters: Dict[ParamID, ParameterCombined]  
###
    
class EnumHelper:
    """Helper to convert strings <-> Enum instances"""

    @staticmethod
    def to_enum(enum_class, value):
        if isinstance(value, enum_class):
            return value
        if isinstance(value, str):
            try:
                return enum_class[value.upper()]
            except KeyError:
                raise ValueError(f"Invalid enum value '{value}' for {enum_class.__name__}")
        raise TypeError(f"Expected str or {enum_class.__name__}, got {type(value)}")

    @staticmethod
    def to_name(value):
        if hasattr(value, "name"):
            return value.name
        return value
          
class DataAssembler:
    def __init__(self, config_dir="config", state_dir="state"):
           
        self.config_dir = Path(config_dir)
        self.state_dir = Path(state_dir)

    def load_yaml(self, name):
        src_dir = Path(__file__).parent.parent
        full_path = src_dir / self.config_dir / name
         
         
        with open(full_path, "r") as f:
            return yaml.safe_load(f)

    def load_json(self, name):
        src_dir = Path(__file__).parent.parent
        full_path = src_dir / self.state_dir / name
         
        with open(full_path, "r") as f:
            return json.load(f)

    def build(self):
        # === Load all configs ===
        params_yaml = self.load_yaml("parameters_new.yaml")
        anims_yaml = self.load_yaml("animations_new.yaml")
        state_json = self.load_json("state_new.json")

        # --- parameters ---
        param_configs = {}
        for section in ["zone_parameters", "animation_base_parameters", "animation_additional_parameters"]:
            for pid_str, data in params_yaml[section].items():
                pid = EnumHelper.to_enum(ParamID, pid_str)
                param_configs[pid] = ParameterConfig(id=pid, **data)

        # --- animations ---
        animations = []
        for aid_str, aconf in anims_yaml["animations"].items():
            aid = EnumHelper.to_enum(AnimationID, aid_str)
            parameters = [EnumHelper.to_enum(ParamID, pid) for pid in aconf["parameters"]]

            anim_conf = AnimationConfig(
                id=aid,
                tag=aconf["tag"],
                display_name=aconf["display_name"],
                description=aconf["description"],
                parameters=parameters
            )
            
            state_data = state_json.get("animations", {}).get(aid_str, {})
            param_values = {
                EnumHelper.to_enum(ParamID, pid): val
                for pid, val in state_data.get("parameters", {}).items()
            }
            
            anim_state = AnimationState(
                id=aid,
                enabled=state_data.get("enabled", False),
                parameter_values=param_values
            )


            # Combine parameters
            params_combined = {
                pid: ParameterCombined(
                    config=param_configs[pid],
                    state=ParameterState(id=pid, value=param_values.get(pid, param_configs[pid].default))
                )
                for pid in parameters
            }
            
            animations.append(AnimationCombined(
                config=anim_conf,
                state=anim_state,
                parameters=params_combined
            ))

        return animations
    
    # --- SERIALIZACJA ---
    def save_state(self, animations, filename="state.json"):
        data = {
            "animations": {
                anim.config.id.name.lower(): {
                    "enabled": anim.state.enabled,
                    "parameters": {
                        EnumHelper.to_name(pid): param.state.value
                        for pid, param in anim.parameters.items()
                    }
                }
                for anim in animations
            }
        }

        src_dir = Path(__file__).parent.parent
        full_path = src_dir / self.state_dir / filename
         
        with open(full_path, "w") as f:
            json.dump(data, f, indent=2)
            

assembler = DataAssembler()
animations = assembler.build()

for anim in animations:
    print(f"▶ {anim.config.display_name}")
    for pid, param in anim.parameters.items():
        print(f"  - {pid.name}: {param.state.value}{param.config.unit or ''}")

# Modyfikacja stanu i zapis
animations[0].parameters[ParamID.ANIM_SPEED].state.value = 80
assembler.save_state(animations)