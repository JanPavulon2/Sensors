import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { useAuth, useCheckBackendConnection } from '@/shared/hooks';

interface MainLayoutProps {
  children: React.ReactNode;
}

export function MainLayout({ children }: MainLayoutProps): JSX.Element {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  const { isAuthenticated, useDefaultTestToken } = useAuth();
  const { isConnected } = useCheckBackendConnection();

  // Initialize with test token on first load if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      useDefaultTestToken();
    }
  }, [isAuthenticated, useDefaultTestToken]);

  const navItems = [
    { label: 'Dashboard', path: '/' },
    { label: 'Components', path: '/components' },
    { label: 'Debug', path: '/debug' },
    { label: 'Settings', path: '/settings' },
  ];

  const isActive = (path: string): boolean => location.pathname === path;

  return (
    <div className="flex h-screen bg-bg-app">
      {/* Sidebar */}
      <aside
        className={`bg-bg-panel border-r border-border transition-all duration-300 ${
          sidebarOpen ? 'w-64' : 'w-20'
        }`}
      >
        {/* Sidebar Header */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-border">
          {sidebarOpen && (
            <div>
              <h1 className="text-xl font-bold text-accent-primary">Diuna</h1>
              <p className="text-xs text-text-tertiary">LED Control</p>
            </div>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="hover:bg-bg-elevated"
          >
            {sidebarOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </Button>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-2">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center justify-center px-4 py-2 rounded-md transition-colors text-sm font-medium ${
                isActive(item.path)
                  ? 'bg-accent-primary text-bg-app'
                  : 'text-text-secondary hover:bg-bg-elevated'
              }`}
            >
              {sidebarOpen && <span>{item.label}</span>}
              {!sidebarOpen && <span className="w-4">{item.label.charAt(0)}</span>}
            </Link>
          ))}
        </nav>

        {/* Footer Info */}
        {sidebarOpen && (
          <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-border bg-bg-panel">
            <div className="text-xs space-y-1">
              <div className="flex items-center gap-2">
                <div
                  className={`w-2 h-2 rounded-full ${
                    isConnected ? 'bg-success' : 'bg-warning'
                  }`}
                />
                <span className="text-text-tertiary">
                  {isConnected ? 'Connected' : 'Connecting...'}
                </span>
              </div>
              <div className="text-text-tertiary">API Ready</div>
            </div>
          </div>
        )}
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 bg-bg-panel border-b border-border flex items-center justify-between px-6">
          <h2 className="text-2xl font-bold text-text-primary">
            {navItems.find((item) => isActive(item.path))?.label || 'Dashboard'}
          </h2>
          <div className="text-sm text-text-secondary">Diuna Frontend v0.1.0</div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-auto p-6">{children}</div>
      </main>
    </div>
  );
}

export default MainLayout;
