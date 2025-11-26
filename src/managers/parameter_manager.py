"""
Parameter Manager - Processes parameter definitions

Processes parameter metadata from ConfigManager (does NOT load files).
Single responsibility: Parse and provide access to parameter definitions with validation.
"""

from typing import Dict, Optional
from models.domain.parameter import ParameterConfig
from models.enums import ParamID, ParameterType
from utils.logger import get_logger
from models.enums import LogLevel, LogCategory

# Module-level logger
log = get_logger().for_category(LogCategory.CONFIG)


class ParameterManager:
    """
    Parameter metadata manager (data processor only)

    Responsibilities:
    - Parse parameter definitions from config data
    - Build Parameter objects with validation rules
    - Provide parameter lookup and metadata access
    - Centralize parameter constraints and behavior

    Does NOT load files - receives data from ConfigManager.

    Example:
        # Created by ConfigManager
        param_mgr = ParameterManager(config_data)

        # Access parameters
        param = param_mgr.get_parameter(ParamID.ZONE_BRIGHTNESS)
        new_value = param.adjust(current_value, delta)
        display_str = param.format_value(new_value)
    """

    def __init__(self, config_data: dict):
        """
        Initialize ParameterManager with parsed config data

        Args:
            config_data: Config dict with parameter sections:
                - 'zone_parameters'
                - 'animation_base_parameters'
                - 'animation_additional_parameters'
        """
        self.parameters: Dict[ParamID, ParameterConfig] = {}
        self._process_data(config_data)

    def _process_data(self, data: dict):
        """
        Process parameter configuration data

        Args:
            data: Config dict with parameter sections

        Raises:
            ValueError: If unknown ParamID referenced or malformed config
        """
        # Parameter sections to load
        sections = [
            'zone_parameters',
            'animation_base_parameters',
            'animation_additional_parameters'
        ]

        param_count = 0
        for section in sections:
            section_data = data.get(section, {})

            for param_name, param_data in section_data.items():
                # Convert string to ParamID enum
                try:
                    param_id = ParamID[param_name]
                except KeyError:
                    log.warn(
                        f"Unknown parameter in {section}",
                        param_name=param_name
                    )
                    continue

                # Convert string to ParameterType enum
                try:
                    param_type = ParameterType[param_data['type']]
                except KeyError:
                    log.warn(
                        f"Unknown ParameterType",
                        param=param_name,
                        type=param_data.get('type')
                    )
                    continue

                # Build Parameter object
                self.parameters[param_id] = ParameterConfig(
                    id=param_id,
                    type=param_type,
                    default=param_data.get('default'),
                    min=param_data.get('min'),
                    max=param_data.get('max'),
                    step=param_data.get('step'),
                    wraps=param_data.get('wraps', False),
                    unit=param_data.get('unit'),
                    description=param_data.get('description', '')
                )
                param_count += 1

        log.info(
            "Parameters loaded",
            total=param_count,
            zone_params=len(data.get('zone_parameters', {})),
            anim_base=len(data.get('animation_base_parameters', {})),
            anim_additional=len(data.get('animation_additional_parameters', {}))
        )

    def get_parameter(self, param_id: ParamID) -> Optional[ParameterConfig]:
        """
        Get parameter definition by ID

        Args:
            param_id: ParamID enum

        Returns:
            Parameter object or None if not found
        """
        return self.parameters.get(param_id)

    def get_all_parameters(self) -> Dict[ParamID, ParameterConfig]:
        """
        Get all parameter definitions

        Returns:
            Dict mapping ParamID to ParameterConfig objects
        """
        return self.parameters.copy()

    def get_zone_parameters(self) -> Dict[ParamID, ParameterConfig]:
        """
        Get only zone parameters (ZONE_*)

        Returns:
            Dict of zone parameters
        """
        return {
            pid: param for pid, param in self.parameters.items()
            if pid.name.startswith('ZONE_')
        }

    def get_animation_parameters(self) -> Dict[ParamID, ParameterConfig]:
        """
        Get only animation parameters (ANIM_*)

        Returns:
            Dict of animation parameters
        """
        return {
            pid: param for pid, param in self.parameters.items()
            if pid.name.startswith('ANIM_')
        }

    def print_summary(self):
        """Log parameter summary for debugging"""
        zone_params = self.get_zone_parameters()
        anim_params = self.get_animation_parameters()

        log.info("=" * 80)
        log.info("PARAMETERS CONFIGURATION")
        log.info("=" * 80)

        log.info(f"\nZone Parameters ({len(zone_params)}):")
        for param_id, param in zone_params.items():
            log.info(f"  {param_id.name:20} {param.type.name:15} default={param.default}")

        log.info(f"\nAnimation Parameters ({len(anim_params)}):")
        for param_id, param in anim_params.items():
            log.info(f"  {param_id.name:20} {param.type.name:15} default={param.default}")

        log.info("-" * 80)
        log.info(f"Total parameters: {len(self.parameters)}")
        log.info("=" * 80)
