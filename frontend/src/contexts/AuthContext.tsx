import React, { createContext, useContext, useState, useEffect } from 'react';

interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  login: (accessToken: string, refreshToken: string, user: User) => void;
  logout: () => void;
  refreshAccessToken: () => Promise<boolean>;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastActivity, setLastActivity] = useState<number>(Date.now());

  // Track user activity
  useEffect(() => {
    const updateActivity = () => {
      setLastActivity(Date.now());
    };

    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
    events.forEach(event => {
      document.addEventListener(event, updateActivity, { passive: true });
    });

    return () => {
      events.forEach(event => {
        document.removeEventListener(event, updateActivity);
      });
    };
  }, []);

  // Auto refresh token based on activity
  useEffect(() => {
    if (!token || !refreshToken || !lastActivity) return;

    const interval = setInterval(() => {
      const now = Date.now();

      // Check if user has been inactive for more than 10 minutes
      if (lastActivity && now - lastActivity > 10 * 60 * 1000) {
        logout();
        return;
      }

      // If user is active, refresh token
      if (lastActivity && now - lastActivity > 5 * 60 * 1000) {
        refreshAccessToken();
      }
    }, 60000); // Check every minute

    return () => clearInterval(interval);
  }, [token, refreshToken, lastActivity]);

  useEffect(() => {
    // Check for existing auth data on app start
    const storedToken = localStorage.getItem('token');
    const storedRefreshToken = localStorage.getItem('refreshToken');
    const storedUser = localStorage.getItem('user');

    if (storedToken && storedRefreshToken && storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser);
        setToken(storedToken);
        setRefreshToken(storedRefreshToken);
        setUser(parsedUser);
        
        // Verify token is still valid
        verifyToken(storedToken);
      } catch (error) {
        console.error('AuthContext: Error parsing stored user data', error);
        // Clear invalid data
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('user');
      }
    }
    
    setIsLoading(false);
  }, []);

  const verifyToken = async (token: string) => {
    try {
      const response = await fetch('/api/users/me', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Token invalid');
      }

      const userData = await response.json();
      setUser(userData);
    } catch (error) {
      // Token is invalid, clear auth data
      logout();
    }
  };

  const login = (accessToken: string, refreshTokenValue: string, user: User) => {
    console.log('AuthContext: Logging in user', user);
    localStorage.setItem('token', accessToken);
    localStorage.setItem('refreshToken', refreshTokenValue);
    localStorage.setItem('user', JSON.stringify(user));
    setToken(accessToken);
    setRefreshToken(refreshTokenValue);
    setUser(user);
  };

  const refreshAccessToken = async (): Promise<boolean> => {
    try {
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }

      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${refreshToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        login(data.access_token, data.refresh_token, data.user);
        return true;
      } else {
        throw new Error('Failed to refresh token');
      }
    } catch (error) {
      console.error('Failed to refresh token:', error);
      logout();
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    setToken(null);
    setRefreshToken(null);
    setUser(null);
  };

  const value: AuthContextType = {
    user,
    token,
    refreshToken,
    login,
    logout,
    refreshAccessToken,
    isAuthenticated: !!user && !!token,
    isLoading,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};