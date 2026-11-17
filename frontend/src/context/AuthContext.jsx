import {
    createContext,
    useContext,
    useEffect,
    useState,
  } from "react";
  
  import { apiRequest } from "../services/api";
  
  const AuthContext = createContext(null);
  
  export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
  
    useEffect(() => {
      const restoreUser = async () => {
        const token =
          localStorage.getItem("access_token");
  
        if (!token) {
          setLoading(false);
          return;
        }
  
        try {
          const currentUser =
            await apiRequest("/api/auth/me");
  
          setUser(currentUser);
        } catch {
          localStorage.removeItem("access_token");
          setUser(null);
        } finally {
          setLoading(false);
        }
      };
  
      restoreUser();
    }, []);
  
    const login = async (email, password) => {
      localStorage.removeItem("access_token");
  
      const formData = new URLSearchParams();
  
      formData.append("username", email);
      formData.append("password", password);
  
      const tokenData = await apiRequest(
        "/api/auth/token",
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/x-www-form-urlencoded",
          },
          body: formData,
        }
      );
  
      localStorage.setItem(
        "access_token",
        tokenData.access_token
      );
  
      const currentUser =
        await apiRequest("/api/auth/me");
  
      setUser(currentUser);
  
      return currentUser;
    };
  
    const logout = () => {
      localStorage.removeItem("access_token");
      setUser(null);
    };
  
    return (
      <AuthContext.Provider
        value={{
          user,
          loading,
          login,
          logout,
        }}
      >
        {children}
      </AuthContext.Provider>
    );
  }
  
  export function useAuth() {
    return useContext(AuthContext);
  }