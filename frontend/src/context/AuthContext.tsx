import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  UserProfile,
  ResearchProject,
} from '../types/api';
import {
  getAuthToken,
  setAuthToken,
  loginApi,
  demoLoginApi,
  logoutApi,
  getMeApi,
  acceptInvitationApi,
  getProjectsApi,
  createProjectApi,
} from '../services/api';

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  isAdmin: boolean;
  isResearcher: boolean;
  isViewer: boolean;
  canEdit: boolean;
  activeProject: ResearchProject | null;
  projects: ResearchProject[];
  login: (email: string, pass: string) => Promise<void>;
  demoLogin: () => Promise<void>;
  logout: () => Promise<void>;
  acceptInvitation: (token: string, fullName: string, pass: string) => Promise<void>;
  setActiveProject: (proj: ResearchProject | null) => void;
  refreshProjects: () => Promise<void>;
  refreshUser: () => Promise<void>;
  createProject: (name: string, description?: string) => Promise<ResearchProject>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(getAuthToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeProject, setActiveProject] = useState<ResearchProject | null>(null);
  const [projects, setProjects] = useState<ResearchProject[]>([]);

  const refreshProjects = useCallback(async () => {
    try {
      const projs = await getProjectsApi();
      setProjects(projs);
      if (projs.length > 0) {
        // Keep active project or select first
        setActiveProject((curr) => {
          if (curr && projs.some((p) => p.id === curr.id)) {
            return curr;
          }
          return projs[0];
        });
      } else {
        setActiveProject(null);
      }
    } catch (e: any) {
      console.warn('Could not load projects:', e.message);
    }
  }, []);

  const refreshUser = useCallback(async () => {
    const currentToken = getAuthToken();
    if (!currentToken) {
      setUser(null);
      setToken(null);
      setIsLoading(false);
      return;
    }

    try {
      const profile = await getMeApi();
      setUser(profile);
      setToken(currentToken);
      await refreshProjects();
    } catch (e: any) {
      console.warn('Session expired or invalid:', e.message);
      setAuthToken(null);
      setUser(null);
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  }, [refreshProjects]);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (email: string, pass: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await loginApi({ email, password: pass });
      setUser(res.user);
      setToken(res.session_token);
      await refreshProjects();
    } catch (e: any) {
      setError(e.message || 'Login failed');
      throw e;
    } finally {
      setIsLoading(false);
    }
  };

  const demoLogin = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await demoLoginApi();
      setUser(res.user);
      setToken(res.session_token);
      await refreshProjects();
    } catch (e: any) {
      setError(e.message || 'Demo login failed');
      throw e;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await logoutApi();
    } catch (e) {
      // Ignore
    } finally {
      setUser(null);
      setToken(null);
      setActiveProject(null);
      setProjects([]);
      setIsLoading(false);
    }
  };

  const acceptInvitation = async (invToken: string, fullName: string, pass: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await acceptInvitationApi({ token: invToken, full_name: fullName, password: pass });
      setUser(res.user);
      setToken(res.session_token);
      await refreshProjects();
    } catch (e: any) {
      setError(e.message || 'Invitation acceptance failed');
      throw e;
    } finally {
      setIsLoading(false);
    }
  };

  const createProject = async (name: string, description?: string): Promise<ResearchProject> => {
    const proj = await createProjectApi({ name, description });
    await refreshProjects();
    setActiveProject(proj);
    return proj;
  };

  const isAdmin = user?.role === 'ADMIN';
  const isResearcher = user?.role === 'RESEARCHER';
  const isViewer = user?.role === 'VIEWER';
  const canEdit = isAdmin || isResearcher;

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        error,
        isAdmin,
        isResearcher,
        isViewer,
        canEdit,
        activeProject,
        projects,
        login,
        demoLogin,
        logout,
        acceptInvitation,
        setActiveProject,
        refreshProjects,
        refreshUser,
        createProject,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
