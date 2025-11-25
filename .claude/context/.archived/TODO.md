# Diuna LED Control System - TODO List

**Last Updated**: 2025-11-03

This document tracks pending tasks, known issues, and planned improvements for the Diuna LED control system.

---

## Critical Issues

### 🔴 Keyboard Input - Evdev Backend Not Working

**Status**: BROKEN - Race condition in evdev library

**Problem**: EvdevKeyboardAdapter detects keyboard device correctly but encounters `asyncio.exceptions.InvalidStateError` when reading events via `async_read_loop()`.

**Root Cause**: Race condition in python-evdev library's async iterator implementation (`evdev/eventio_async.py:45`).

**Error**:
```
Exception in callback ReadIterator.__anext__.<locals>.next_batch_ready(...)
asyncio.exceptions.InvalidStateError: invalid state
```

**Attempted Fixes**:
1. ✗ Device grab (`device.grab()`) - didn't help
2. ✗ Manual polling with `run_in_executor()` - caused EAGAIN errors
3. ✗ Using `read_one()` instead of `read()` - still errors

**Current Workaround**: StdinKeyboardAdapter works and is used as fallback

**Next Steps**:
1. Try alternative evdev library (e.g., `evdev-rs`, `libevdev` bindings)
2. Implement custom /dev/input reader using `select()` or `epoll()`
3. Use synchronous `read()` in thread pool executor with proper file descriptor setup
4. Consider using `asyncio.add_reader()` with file descriptor

**Impact**: Physical keyboard input not available, only stdin mode works

**Files Affected**:
- `src/components/keyboard/evdev_keyboard_adapter.py` (lines 264-270)

**Priority**: Medium (stdin mode is sufficient for current development)

---

## Known Limitations

### Keyboard Input - Stdin Mode

**Working Scenarios**:
- ✅ Arrow keys (UP, DOWN, LEFT, RIGHT)
- ✅ Enter key
- ✅ Letter keys (A-Z)
- ✅ Number keys (0-9)
- ✅ Space, Tab, Backspace, Escape
- ✅ Ctrl+letter combinations
- ✅ Shift detection (uppercase letters and shifted symbols)

**Limitations**:
1. **Alt key not detected**
   - Left Alt sends ESC sequence (indistinguishable from ESC key)
   - Right Alt (AltGr) sends UTF-8 special characters (Ä, Å, etc.)
   - **Reason**: Terminal limitation, not fixable in stdin mode

2. **Requires 2x Ctrl+C to exit**
   - First Ctrl+C: Cancels main event loop
   - Second Ctrl+C: Unblocks stdin.read() in executor thread
   - **Reason**: Blocking read in executor thread cannot be interrupted
   - **Workaround**: Use evdev mode when fixed (instant shutdown)

3. **VSCode keyboard shortcuts override Ctrl combinations**
   - Ctrl+S, Ctrl+F, etc. intercepted by VSCode
   - **Reason**: VSCode has priority over terminal input
   - **Workaround**: Disable VSCode shortcuts or use different key bindings

4. **Shift detection doesn't work with Caps Lock**
   - Detection based on uppercase character = Shift pressed
   - Caps Lock uppercase letters incorrectly detected as Shift
   - **Reason**: Terminal doesn't send modifier flags
   - **Impact**: Minor - only affects testing scenarios

**Files Affected**:
- `src/components/keyboard/stdin_keyboard_adapter.py`

---

## Planned Improvements

### High Priority

- [ ] **Fix evdev keyboard backend** (see Critical Issues above)
- [ ] **Add keyboard event handlers to LEDController**
  - Left/Right arrows: Zone navigation
  - Space: Toggle edit mode
  - Other keys: TBD based on user requirements

### Medium Priority

- [ ] **Improve keyboard device detection**
  - Filter for devices with full keyboard capabilities
  - Prefer devices with `/dev/input/by-id/` symlinks containing "kbd"
  - Add device priority scoring (more keys = higher priority)

- [ ] **Add keyboard configuration to hardware.yaml**
  ```yaml
  keyboard:
    enabled: true
    device_path: null  # Auto-detect
    fallback_to_stdin: true
  ```

- [ ] **Add keyboard input documentation to CLAUDE.md**
  - Usage examples
  - Key mappings
  - Troubleshooting guide

### Low Priority

- [ ] **Add keyboard input to logging system**
  - Create dedicated log category (already exists: `LogCategory.EVENT`)
  - Add structured logging for key press events

- [ ] **Implement key repeat handling**
  - Currently only KEY_DOWN events published
  - Add optional KEY_HOLD/KEY_REPEAT support for continuous actions

- [ ] **Add keyboard input tests**
  - Mock evdev device
  - Test modifier tracking
  - Test escape sequence handling

---

## Technical Debt

### Code Quality

- [ ] **Clean up evdev_keyboard_adapter.py commented code**
  - Remove old `_handle_key_event()` implementation (lines 341-413)
  - Remove unused `_read_events()` method (lines 288-301)

- [ ] **Standardize error handling**
  - Consistent exception handling across keyboard adapters
  - Better error messages for device access failures

### Documentation

- [x] **Update ARCHITECTURE.md with keyboard system** (DONE)
- [ ] **Add keyboard system to CLAUDE.md**
- [ ] **Document keyboard input limitations in README**

---

## Future Features

### Keyboard Enhancements

- [ ] **Configurable key mappings**
  - YAML configuration for key bindings
  - Allow user-defined shortcuts

- [ ] **Multi-key combinations**
  - Support Ctrl+Shift+Key
  - Support Alt+Shift+Key (when evdev works)

- [ ] **Macro support**
  - Record key sequences
  - Playback macros for testing

### Alternative Input Sources

- [ ] **Web API input** (already planned in architecture)
  - REST API for remote control
  - WebSocket for real-time updates

- [ ] **MQTT input** (already planned in architecture)
  - Subscribe to MQTT topics
  - Publish state changes

- [ ] **Mobile app input**
  - Bluetooth LE input
  - Or web-based mobile UI

---

## Investigation Needed

### Evdev Race Condition

**Question**: Can we use synchronous evdev with asyncio?

**Approach**:
```python
def _blocking_read(device):
    """Synchronous read (runs in thread pool)"""
    return device.read_one()  # Blocks until event

# In async context
event = await loop.run_in_executor(None, _blocking_read, self.device)
```

**Concerns**:
- File descriptor setup (blocking vs non-blocking)
- Thread pool overhead
- Event buffering

**Action**: Research evdev device modes and file descriptor flags

### Alternative Libraries

**Options to investigate**:
1. **python-libevdev** - Python bindings for libevdev
   - More stable than python-evdev?
   - Check async support

2. **evdev-rs** - Rust-based evdev bindings
   - May have better async support
   - Check Python FFI overhead

3. **Custom implementation** - Direct /dev/input reading
   - Use `select()` or `epoll()` with asyncio
   - Parse input_event struct manually
   - Full control over async behavior

**Action**: Create proof-of-concept for each option

---

## Completed Tasks

- [x] Implement KeyboardInputAdapter with dual backend
- [x] Implement StdinKeyboardAdapter (WORKING)
- [x] Implement EvdevKeyboardAdapter (device detection working)
- [x] Add KeyboardKeyPressEvent to event system
- [x] Add LogCategory.EVENT to enums
- [x] Integrate keyboard adapter into main_asyncio.py
- [x] Update ARCHITECTURE.md with keyboard system documentation
- [x] Move keyboard files to components/keyboard/ subfolder
- [x] Create comprehensive TODO list

---

## Notes

### Development Guidelines

**When working on keyboard input**:
1. Always test with both evdev and stdin backends
2. Test modifier combinations thoroughly
3. Test escape sequences for arrow keys
4. Document any terminal-specific behavior
5. Add logging for debugging

**Testing checklist**:
- [ ] Device detection works
- [ ] Arrow keys detected correctly
- [ ] Modifiers tracked correctly (Ctrl, Shift)
- [ ] Special keys work (Enter, Tab, Space, Backspace, Escape)
- [ ] Shutdown is clean (no hanging threads)
- [ ] Events published to EventBus correctly

### Performance Considerations

**Keyboard input is not performance-critical**:
- Human typing speed: ~5-10 keys/second max
- System can handle 100+ events/second easily
- Focus on correctness over optimization

---

**END OF TODO LIST**
