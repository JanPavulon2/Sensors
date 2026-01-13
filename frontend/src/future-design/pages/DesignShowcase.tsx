/**
 * Design Showcase Page - Future Design UX/UI System
 * Component library and live demo of the future LED control interface
 *
 * Accessible at: /future-design
 */

import React, { useEffect } from 'react';
import { Button } from '@/shared/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card';
import { useDesignTheme, useThemeSwitch, initializeDesignStore } from '../store/designStore';
import { getDefaultPresets } from '../utils/colors';
import styles from './DesignShowcase.module.css';

// Import design system styles
import '../styles/design-tokens.css';
import '../styles/theme-cyber.css';
import '../styles/theme-nature.css';

interface SectionProps {
  title: string;
  description: string;
  children: React.ReactNode;
}

const Section: React.FC<SectionProps> = ({ title, description, children }) => (
  <section className={styles.section}>
    <h2 className={styles.sectionTitle}>{title}</h2>
    <p className={styles.sectionDescription}>{description}</p>
    <div className={styles.sectionContent}>{children}</div>
  </section>
);

/**
 * Design Showcase Component
 * Demonstrates all Phase 1 components and design system
 */
export const DesignShowcase: React.FC = () => {
  const theme = useDesignTheme();
  const { toggleTheme } = useThemeSwitch();

  // Initialize store on mount
  useEffect(() => {
    initializeDesignStore();
  }, []);

  const colorPresets = getDefaultPresets();
  const basicPresets = colorPresets.filter((p) => p.category === 'basic');
  const warmPresets = colorPresets.filter((p) => p.category === 'warm');
  const coolPresets = colorPresets.filter((p) => p.category === 'cool');
  const naturalPresets = colorPresets.filter((p) => p.category === 'natural');
  const whitePresets = colorPresets.filter((p) => p.category === 'white');

  return (
    <div className={`design-showcase ${theme}-theme`}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <div>
            <h1 className={styles.title}>🎨 Diuna Future Design System</h1>
            <p className={styles.subtitle}>
              Phase 1: LED Strip Control • Real-time Visualization • Advanced Color & Animation Control
            </p>
          </div>

          <Button
            onClick={toggleTheme}
            variant="outline"
            className={styles.themeToggle}
            title={`Switch to ${theme === 'cyber' ? 'nature' : 'cyber'} theme`}
          >
            {theme === 'cyber' ? '🌲 Nature' : '🔌 Cyber'}
          </Button>
        </div>
      </header>

      <main className={styles.mainContent}>
        {/* ============ Introduction ============ */}
        <Section
          title="Welcome to Diuna Future Design"
          description="This showcase demonstrates the complete UX/UI design for managing addressable LED strips. Start exploring the components below!"
        >
          <div className={styles.introGrid}>
            <Card>
              <CardHeader>
                <CardTitle>🎬 Phase 1: Foundation</CardTitle>
              </CardHeader>
              <CardContent>
                <p>Single LED strip visualization and control with basic color & animation management</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>🎯 Key Features</CardTitle>
              </CardHeader>
              <CardContent>
                <ul>
                  <li>Realistic LED visualization with glow effects</li>
                  <li>Real-time WebSocket synchronization (60 FPS)</li>
                  <li>Advanced color control (HUE, RGB, PRESET modes)</li>
                  <li>6 animation types with parameter control</li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>🎨 Design Philosophy</CardTitle>
              </CardHeader>
              <CardContent>
                <ul>
                  <li>Realistic & engaging visualization</li>
                  <li>Progressive complexity (easy for beginners, powerful for experts)</li>
                  <li>Aesthetic fusion (cyberpunk + nature)</li>
                  <li>Mobile-first responsive design</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </Section>

        {/* ============ Color System ============ */}
        <Section
          title="Color System Showcase"
          description="Three intuitive color control modes: HUE wheel, RGB sliders, and preset colors"
        >
          <div className={styles.colorSystemGrid}>
            {/* Color Presets Display */}
            <Card>
              <CardHeader>
                <CardTitle>Preset Colors</CardTitle>
                <CardDescription>20 curated colors organized by category</CardDescription>
              </CardHeader>
              <CardContent className={styles.presetsContent}>
                <div className={styles.presetCategory}>
                  <h4>Basic Colors</h4>
                  <div className={styles.presetGrid}>
                    {basicPresets.map((preset) => (
                      <div
                        key={preset.name}
                        className={styles.presetSwatch}
                        style={{ backgroundColor: preset.hex }}
                        title={preset.name}
                      />
                    ))}
                  </div>
                </div>

                <div className={styles.presetCategory}>
                  <h4>Warm Tones</h4>
                  <div className={styles.presetGrid}>
                    {warmPresets.map((preset) => (
                      <div
                        key={preset.name}
                        className={styles.presetSwatch}
                        style={{ backgroundColor: preset.hex }}
                        title={preset.name}
                      />
                    ))}
                  </div>
                </div>

                <div className={styles.presetCategory}>
                  <h4>Cool Tones</h4>
                  <div className={styles.presetGrid}>
                    {coolPresets.map((preset) => (
                      <div
                        key={preset.name}
                        className={styles.presetSwatch}
                        style={{ backgroundColor: preset.hex }}
                        title={preset.name}
                      />
                    ))}
                  </div>
                </div>

                <div className={styles.presetCategory}>
                  <h4>Natural Tones</h4>
                  <div className={styles.presetGrid}>
                    {naturalPresets.map((preset) => (
                      <div
                        key={preset.name}
                        className={styles.presetSwatch}
                        style={{ backgroundColor: preset.hex }}
                        title={preset.name}
                      />
                    ))}
                  </div>
                </div>

                <div className={styles.presetCategory}>
                  <h4>Whites</h4>
                  <div className={styles.presetGrid}>
                    {whitePresets.map((preset) => (
                      <div
                        key={preset.name}
                        className={styles.presetSwatch}
                        style={{ backgroundColor: preset.hex }}
                        title={preset.name}
                      />
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Color Modes Info */}
            <div className={styles.colorModesInfo}>
              <Card>
                <CardHeader>
                  <CardTitle>HUE Mode</CardTitle>
                  <CardDescription>360° circular color wheel</CardDescription>
                </CardHeader>
                <CardContent>
                  <p>Intuitive color selection via circular hue picker. Perfect for quick color changes.</p>
                  <div className={styles.modeExample}>
                    <div className={styles.hueWheel} />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>RGB Mode</CardTitle>
                  <CardDescription>Precise 0-255 channel control</CardDescription>
                </CardHeader>
                <CardContent>
                  <p>Direct RGB control with three sliders and hex input/output.</p>
                  <div className={styles.rgbSliders}>
                    <div className={styles.sliderLabel}>R: 255</div>
                    <div className={styles.slider} style={{ backgroundColor: 'rgba(255, 0, 0, 0.2)' }} />
                    <div className={styles.sliderLabel}>G: 0</div>
                    <div className={styles.slider} style={{ backgroundColor: 'rgba(0, 255, 0, 0.2)' }} />
                    <div className={styles.sliderLabel}>B: 0</div>
                    <div className={styles.slider} style={{ backgroundColor: 'rgba(0, 0, 255, 0.2)' }} />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>PRESET Mode</CardTitle>
                  <CardDescription>One-click color selection</CardDescription>
                </CardHeader>
                <CardContent>
                  <p>Quick access to 20 curated preset colors organized by category.</p>
                  <div className={styles.presetQuick}>
                    {basicPresets.slice(0, 3).map((preset) => (
                      <div
                        key={preset.name}
                        className={styles.presetQuickItem}
                        style={{ backgroundColor: preset.hex }}
                      />
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </Section>

        {/* ============ LED Visualization ============ */}
        <Section
          title="LED Visualization"
          description="Realistic LED strip rendering with glow effects, color bleeding, and brightness scaling"
        >
          <Card>
            <CardHeader>
              <CardTitle>LED Strip Canvas</CardTitle>
              <CardDescription>Horizontal strip with glow effects (coming soon)</CardDescription>
            </CardHeader>
            <CardContent>
              <div className={styles.canvasPlaceholder}>
                <p>🎨 LED Canvas component coming soon</p>
                <p>Features: Realistic glow, color bleeding, zoom, pan, zone overlay</p>
              </div>
            </CardContent>
          </Card>
        </Section>

        {/* ============ Animation System ============ */}
        <Section
          title="Animation System"
          description="6 animation types with configurable parameters and live preview"
        >
          <div className={styles.animationsGrid}>
            <Card>
              <CardHeader>
                <CardTitle>⊙ BREATHE</CardTitle>
                <CardDescription>Smooth sine wave pulsing</CardDescription>
              </CardHeader>
              <CardContent>
                <p>Parameters: Speed, Intensity, Color</p>
                <p>Perfect for ambient mood lighting and attention indicators.</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>🌈 COLOR_FADE</CardTitle>
                <CardDescription>Rainbow hue spectrum cycling</CardDescription>
              </CardHeader>
              <CardContent>
                <p>Parameters: Speed, Intensity</p>
                <p>Creates calming gradient transitions through full hue spectrum.</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>🎨 COLOR_CYCLE</CardTitle>
                <CardDescription>RGB color stepping</CardDescription>
              </CardHeader>
              <CardContent>
                <p>Fixed red → green → blue cycling</p>
                <p>Simple, clear state transitions for testing and basic feedback.</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>🐍 SNAKE</CardTitle>
                <CardDescription>Single pixel traveling chase</CardDescription>
              </CardHeader>
              <CardContent>
                <p>Parameters: Speed, Length, Color</p>
                <p>Great for loading animations and activity indicators.</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>🌈🐍 COLOR_SNAKE</CardTitle>
                <CardDescription>Rainbow gradient chase effect</CardDescription>
              </CardHeader>
              <CardContent>
                <p>Parameters: Speed, Length, Color, Hue Offset</p>
                <p>High-energy animated effect for party and gaming modes.</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>📟 MATRIX (Disabled)</CardTitle>
                <CardDescription>Code rain effect</CardDescription>
              </CardHeader>
              <CardContent>
                <p>Parameters: Speed, Length, Intensity, Color</p>
                <p>Per-zone independent falling drops with fading tail.</p>
              </CardContent>
            </Card>
          </div>
        </Section>

        {/* ============ Zone Management ============ */}
        <Section
          title="Zone Management"
          description="Individual LED strip zone control with colors, brightness, modes"
        >
          <Card>
            <CardHeader>
              <CardTitle>Zone Card Component</CardTitle>
              <CardDescription>Compact view of zone state and quick controls</CardDescription>
            </CardHeader>
            <CardContent className={styles.zoneCardDemo}>
              <div className={styles.demoZoneCard}>
                <div className={styles.zoneCardHeader}>
                  <span className={styles.zoneName}>FLOOR</span>
                  <span className={styles.zoneStatus}>● ON</span>
                </div>
                <div className={styles.zonePreview}>
                  <div className={styles.pixelRow}>
                    {Array.from({ length: 6 }).map((_, i) => (
                      <div
                        key={i}
                        className={styles.pixelDemo}
                        style={{
                          backgroundColor: `hsl(${i * 60}, 100%, 50%)`,
                          boxShadow: `0 0 8px hsl(${i * 60}, 100%, 50%), 0 0 16px hsl(${i * 60}, 100%, 50%)`,
                        }}
                      />
                    ))}
                  </div>
                </div>
                <div className={styles.zoneInfo}>
                  <span>18 pixels</span>
                  <span>ANIMATION (Breathe)</span>
                </div>
                <div className={styles.zoneControls}>
                  <span>Brightness: 25%</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </Section>

        {/* ============ Design Tokens ============ */}
        <Section
          title="Design Tokens & Theming"
          description="Complete color system and CSS custom properties for consistent design"
        >
          <div className={styles.tokensGrid}>
            <Card>
              <CardHeader>
                <CardTitle>Current Theme Colors</CardTitle>
                <CardDescription>{theme === 'cyber' ? '🔌 Cyber' : '🌲 Nature'}</CardDescription>
              </CardHeader>
              <CardContent className={styles.tokenColors}>
                <div className={styles.tokenColor}>
                  <div className={styles.colorSwatch} style={{ backgroundColor: 'var(--theme-background)' }} />
                  <span>Background</span>
                </div>
                <div className={styles.tokenColor}>
                  <div className={styles.colorSwatch} style={{ backgroundColor: 'var(--theme-surface)' }} />
                  <span>Surface</span>
                </div>
                <div className={styles.tokenColor}>
                  <div className={styles.colorSwatch} style={{ backgroundColor: 'var(--theme-accent-primary)' }} />
                  <span>Accent Primary</span>
                </div>
                <div className={styles.tokenColor}>
                  <div className={styles.colorSwatch} style={{ backgroundColor: 'var(--theme-accent-secondary)' }} />
                  <span>Accent Secondary</span>
                </div>
                <div className={styles.tokenColor}>
                  <div className={styles.colorSwatch} style={{ backgroundColor: 'var(--theme-accent-tertiary)' }} />
                  <span>Accent Tertiary</span>
                </div>
                <div className={styles.tokenColor}>
                  <div className={styles.colorSwatch} style={{ backgroundColor: 'var(--theme-text)' }} />
                  <span>Text</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Theme Variants</CardTitle>
              </CardHeader>
              <CardContent className={styles.themeInfo}>
                <div>
                  <h5>🔌 Cyber Theme</h5>
                  <p>Futuristic, circuit-inspired with bioluminescent accents (cyan, purple, green neon)</p>
                </div>
                <div>
                  <h5>🌲 Nature Theme</h5>
                  <p>Organic, forest-inspired with warm earth tones (green, orange, gold)</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </Section>

        {/* ============ Component Status ============ */}
        <Section title="Implementation Status" description="Phase 1 Component Progress">
          <Card>
            <CardContent className={styles.statusTable}>
              <table>
                <thead>
                  <tr>
                    <th>Component</th>
                    <th>Status</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Design Store</td>
                    <td className={styles.statusDone}>✅ Done</td>
                    <td>Zustand store with theme, zones, colors, animations</td>
                  </tr>
                  <tr>
                    <td>Color Utilities</td>
                    <td className={styles.statusDone}>✅ Done</td>
                    <td>HUE/RGB/Hex conversions, brightness, presets</td>
                  </tr>
                  <tr>
                    <td>Design Tokens & Themes</td>
                    <td className={styles.statusDone}>✅ Done</td>
                    <td>CSS tokens, cyber & nature themes</td>
                  </tr>
                  <tr>
                    <td>LED Canvas Renderer</td>
                    <td className={styles.statusWip}>🚧 In Progress</td>
                    <td>Canvas-based LED visualization with glow</td>
                  </tr>
                  <tr>
                    <td>Hue Wheel Picker</td>
                    <td className={styles.statusWip}>🚧 In Progress</td>
                    <td>Circular 360° color selector</td>
                  </tr>
                  <tr>
                    <td>RGB Sliders</td>
                    <td className={styles.statusWip}>🚧 In Progress</td>
                    <td>Three sliders for RGB control</td>
                  </tr>
                  <tr>
                    <td>Preset Color Grid</td>
                    <td className={styles.statusWip}>🚧 In Progress</td>
                    <td>Grid of 20 categorized color presets</td>
                  </tr>
                  <tr>
                    <td>Animation Controls</td>
                    <td className={styles.statusWip}>🚧 In Progress</td>
                    <td>Animation selector & parameter sliders</td>
                  </tr>
                  <tr>
                    <td>Zone Cards</td>
                    <td className={styles.statusWip}>🚧 In Progress</td>
                    <td>Compact zone control cards</td>
                  </tr>
                </tbody>
              </table>
            </CardContent>
          </Card>
        </Section>

        {/* ============ Next Steps ============ */}
        <Section
          title="Next Steps"
          description="Upcoming implementation roadmap"
        >
          <div className={styles.nextStepsGrid}>
            <Card>
              <CardHeader>
                <CardTitle>Phase 1: Current</CardTitle>
              </CardHeader>
              <CardContent>
                <ol>
                  <li>✅ Documentation & design specs</li>
                  <li>✅ Setup project structure</li>
                  <li>🚧 LED Canvas Renderer</li>
                  <li>🚧 Color Control System</li>
                  <li>🚧 Animation Controls</li>
                  <li>🚧 Zone Management</li>
                </ol>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Phase 2: Multi-Zone</CardTitle>
              </CardHeader>
              <CardContent>
                <ol>
                  <li>Zone grouping system</li>
                  <li>Scene save/load</li>
                  <li>Layout editor</li>
                  <li>Batch operations</li>
                </ol>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Phase 3+: Advanced</CardTitle>
              </CardHeader>
              <CardContent>
                <ol>
                  <li>Animation timeline editor</li>
                  <li>Custom animation builder</li>
                  <li>Palette creator with image import</li>
                  <li>3D preview & clothing design</li>
                </ol>
              </CardContent>
            </Card>
          </div>
        </Section>
      </main>

      <footer className={styles.footer}>
        <p>
          🎨 Diuna Future Design System • Phase 1: LED Strip Control •
          {' '}
          <a href="/future-design/docs" target="_blank" rel="noopener noreferrer">
            Documentation
          </a>
        </p>
      </footer>
    </div>
  );
};

export default DesignShowcase;
