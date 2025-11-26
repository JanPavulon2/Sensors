export function Dashboard(): JSX.Element {
  return (
    <div className="flex h-screen bg-bg-app">
      {/* Sidebar */}
      <aside className="w-72 bg-bg-panel border-r border-border-default p-6">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-accent-primary">Diuna</h1>
          <p className="text-sm text-text-tertiary mt-2">LED Control & Animation</p>
        </div>

        {/* Placeholder sections */}
        <div className="space-y-6">
          <div>
            <h3 className="text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-3">
              Zones
            </h3>
            <div className="space-y-2">
              <p className="text-sm text-text-secondary">No zones loaded</p>
            </div>
          </div>

          <div>
            <h3 className="text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-3">
              System Status
            </h3>
            <div className="text-sm">
              <p className="text-text-secondary">Connection: <span className="text-error">Disconnected</span></p>
              <p className="text-text-secondary">FPS: <span className="text-text-primary">--</span></p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        {/* Header */}
        <header className="h-16 border-b border-border-default flex items-center justify-between px-6 bg-bg-panel">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-semibold">Dashboard</h2>
          </div>
          <div className="text-sm text-text-secondary">
            Ready to connect
          </div>
        </header>

        {/* Canvas Area */}
        <div className="flex-1 p-6 flex items-center justify-center">
          <div className="text-center">
            <div className="w-16 h-16 bg-bg-panel rounded-lg mx-auto mb-4 flex items-center justify-center">
              <span className="text-2xl text-text-tertiary">⚡</span>
            </div>
            <h3 className="text-lg font-medium mb-2">Welcome to Diuna</h3>
            <p className="text-text-secondary max-w-md">
              Connect to the LED system backend to start controlling zones and running animations.
            </p>
          </div>
        </div>

        {/* Footer Controls */}
        <div className="h-20 border-t border-border-default px-6 flex items-center gap-4 bg-bg-panel">
          <div className="text-sm text-text-secondary">
            Configure backend connection in settings
          </div>
        </div>
      </main>
    </div>
  );
}

export default Dashboard;
