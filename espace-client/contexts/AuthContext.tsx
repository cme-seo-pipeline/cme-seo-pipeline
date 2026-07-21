"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut as firebaseSignOut,
  sendEmailVerification,
  sendPasswordResetEmail,
  User,
} from "firebase/auth";
import { auth } from "@/lib/firebase";

interface RegisterData {
  email: string;
  password: string;
  nom: string;
  prenom: string;
  telephone: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  emailVerified: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  getToken: () => Promise<string | null>;
  resendVerification: () => Promise<void>;
  refreshEmailStatus: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_URL = process.env.NEXT_PUBLIC_CLIENT_API_URL;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [emailVerified, setEmailVerified] = useState(false);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      setUser(firebaseUser);
      setEmailVerified(firebaseUser?.emailVerified ?? false);
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  async function login(email: string, password: string) {
    await signInWithEmailAndPassword(auth, email, password);
  }

  async function register(data: RegisterData) {
    // Le compte est cree cote serveur par cme-client-api (deja teste en Sprint 1),
    // qui cree a la fois le compte Firebase Auth ET le document Firestore.
    const res = await fetch(`${API_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || "Erreur lors de l'inscription");
    }
    // Une fois le compte cree, on connecte immediatement l'utilisateur
    // (le SDK client a besoin de sa propre session, distincte de la creation serveur)
    await signInWithEmailAndPassword(auth, data.email, data.password);

    // Envoi automatique de l'email de verification a la creation du compte.
    // Non bloquant : le compte reste utilisable meme si l'envoi echoue.
    if (auth.currentUser) {
      try {
        await sendEmailVerification(auth.currentUser);
      } catch {
        // silencieux
      }
    }
  }

  async function logout() {
    await firebaseSignOut(auth);
  }

  async function getToken(): Promise<string | null> {
    if (!auth.currentUser) return null;
    return auth.currentUser.getIdToken();
  }

  async function resendVerification() {
    if (auth.currentUser) {
      await sendEmailVerification(auth.currentUser);
    }
  }

  async function refreshEmailStatus() {
    if (auth.currentUser) {
      await auth.currentUser.reload();
      setEmailVerified(auth.currentUser.emailVerified);
    }
  }

  async function resetPassword(email: string) {
    await sendPasswordResetEmail(auth, email);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        emailVerified,
        login,
        register,
        logout,
        getToken,
        resendVerification,
        refreshEmailStatus,
        resetPassword,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth doit etre utilise a l'interieur d'un AuthProvider");
  }
  return context;
}
