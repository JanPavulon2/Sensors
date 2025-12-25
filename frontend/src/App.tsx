import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { MainLayout } from '@/layout/MainLayout';
import Dashboard from '@/pages/Dashboard';
import ComponentsPage from '@/pages/ComponentsPage';
import SettingsPage from '@/pages/SettingsPage';
import { DebugPage } from '@/pages/DebugPage';
import NotFound from '@/pages/NotFound';
import DesignShowcase from '@/future-design/pages/DesignShowcase';
import ControlPanel from '@/future-design/pages/ControlPanel';
import ZonesDashboardPage from '@/future-design/pages/ZonesDashboardPage';

// Create a client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

export function App(): JSX.Element {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          {/* Future Design System - Full page showcase */}
          <Route path="/future-design" element={<DesignShowcase />} />
          <Route path="/future-design/control" element={<ControlPanel />} />
          <Route path="/future-design/dashboard" element={<ZonesDashboardPage />} />

          {/* Main app with layout */}
          <Route
            path="/*"
            element={
              <MainLayout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/components" element={<ComponentsPage />} />
                  <Route path="/debug" element={<DebugPage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                  <Route path="*" element={<NotFound />} />
                </Routes>
              </MainLayout>
            }
          />
        </Routes>
      </Router>
      <Toaster position="top-right" theme="dark" />
    </QueryClientProvider>
  );
}

export default App;
