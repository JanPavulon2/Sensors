/**
 * Display Formatters
 * Format data for display purposes
 */

/**
 * Format uptime in seconds to readable string
 */
export function formatUptime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  const parts = [];
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);

  return parts.join(' ');
}

/**
 * Format power in watts
 */
export function formatPower(watts: number): string {
  if (watts > 1000) {
    return `${(watts / 1000).toFixed(1)}kW`;
  }
  return `${watts.toFixed(0)}W`;
}

/**
 * Format FPS for display
 */
export function formatFps(fps: number): string {
  return fps.toFixed(1);
}

/**
 * Format brightness percentage (0-255 to 0-100%)
 */
export function formatBrightness(value: number): string {
  const percent = Math.round((value / 255) * 100);
  return `${percent}%`;
}

/**
 * Format temperature in Celsius
 */
export function formatTemperature(celsius: number): string {
  return `${celsius.toFixed(1)}°C`;
}

/**
 * Truncate string with ellipsis
 */
export function truncateString(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return `${str.substring(0, maxLength)}...`;
}
