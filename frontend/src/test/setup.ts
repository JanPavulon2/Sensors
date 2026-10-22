import '@testing-library/jest-dom';

// jsdom doesn't implement ResizeObserver - needed by canvas-based components
// like HueWheelPicker, which weren't exercised by any test before this suite.
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof globalThis.ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver;
}
