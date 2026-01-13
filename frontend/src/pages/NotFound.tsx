import { useNavigate } from 'react-router-dom';

export function NotFound(): JSX.Element {
  const navigate = useNavigate();

  return (
    <div className="flex h-screen items-center justify-center bg-bg-app">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-accent-primary mb-4">404</h1>
        <h2 className="text-2xl font-semibold text-text-primary mb-2">Page not found</h2>
        <p className="text-text-secondary mb-8">
          The page you're looking for doesn't exist.
        </p>
        <button
          onClick={() => navigate('/')}
          className="px-6 py-2 bg-accent-primary text-bg-app font-medium rounded-md hover:bg-accent-hover transition-colors"
        >
          Return to Dashboard
        </button>
      </div>
    </div>
  );
}

export default NotFound;
