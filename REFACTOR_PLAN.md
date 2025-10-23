# Refactoring Plan - Color Model Migration

## Problem
LED Controller ma **nowy Color model** (lines 190-204) ale **nie używa go** (uses old zone_hues dict).

Current state:
```python
# NEW model (created but unused)
self.zone_colors = {}  # Dict[str, Color]

# OLD dicts (still used everywhere)
self.zone_hues = {z: self.zone_colors[z].to_hue() for z in self.zone_names}  # Line 211
self.zone_preset_indices = {z: 0 for z in self.zone_names}  # Line 212
```

## Solution: Complete the migration

### Step 1: Replace all zone_hues usage with zone_colors

**OLD CODE**:
```python
# Line 289, 423, 461, 527, 555, etc.
hue = self.zone_hues[zone_name]
r, g, b = hue_to_rgb(hue)
```

**NEW CODE**:
```python
r, g, b = self.zone_colors[zone_name].to_rgb()
```

### Step 2: Replace color adjustment logic

**OLD CODE (line 553-570)**:
```python
if self.color_mode == ColorMode.HUE:
    self.zone_hues[zone_name] = (self.zone_hues[zone_name] + delta) % 360
    hue = self.zone_hues[zone_name]
    r, g, b = hue_to_rgb(hue)
else:  # PRESET
    self.zone_preset_indices[zone_name] = (...)
    preset_name, (r, g, b) = get_preset_by_index(preset_idx)
    hue = rgb_to_hue(r, g, b)
    self.zone_hues[zone_name] = hue
```

**NEW CODE**:
```python
if self.color_mode == ColorMode.HUE:
    self.zone_colors[zone_name] = self.zone_colors[zone_name].adjust_hue(delta)
else:  # PRESET
    self.zone_colors[zone_name] = self.zone_colors[zone_name].next_preset(delta, self.color_manager)
```

### Step 3: Update state serialization

**OLD CODE (line 1609-1616)**:
```python
"zones": {
    zone: {
        "hue": self.zone_hues[zone],
        "brightness": self.zone_brightness[zone],
        "preset": self.zone_preset_indices[zone]
    }
    for zone in self.zone_names
}
```

**NEW CODE**:
```python
"zones": {
    zone: {
        "color": self.zone_colors[zone].to_dict(),
        "brightness": self.zone_brightness[zone]
    }
    for zone in self.zone_names
}
```

### Step 4: Remove legacy dicts

**DELETE**:
```python
# Line 211-212
self.zone_hues = {z: self.zone_colors[z].to_hue() for z in self.zone_names}
self.zone_preset_indices = {z: 0 for z in self.zone_names}
```

## Files to change

1. **src/led_controller.py** - Complete Color model migration
2. **src/managers/hardware_manager.py** - Remove `@property hardware` (line 160-172)
3. **src/managers/config_manager.py** - Inject ZoneManager instead of creating it internally
4. **src/models/parameter.py** - Remove auto-load on import (line 275-282)

## Benefits

✅ **Single Source of Truth**: `zone_colors[zone].to_rgb()` handles HUE/PRESET/WHITE automatically
✅ **White Presets Work**: RGB cache preserves exact (255, 200, 150) for warm_white
✅ **Cleaner Code**: No manual HUE/PRESET synchronization
✅ **Type Safety**: Color object instead of multiple dicts

## Testing checklist

- [ ] HUE mode adjustment works (adjust_hue)
- [ ] PRESET mode cycling works (next_preset)
- [ ] White presets render exact RGB (warm_white, white, cool_white)
- [ ] State save/load preserves colors
- [ ] Pulsing uses Color.to_rgb()
- [ ] Animations use Color.to_rgb()
