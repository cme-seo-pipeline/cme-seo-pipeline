import { useEffect, useState } from "react";
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity } from "react-native";
import { router } from "expo-router";
import { useAuth } from "../contexts/AuthContext";

const API_URL = process.env.EXPO_PUBLIC_CLIENT_API_URL;

interface Profil {
  prenom?: string;
  nom?: string;
  email?: string;
}

export default function HomeScreen() {
  const { user, loading, logout, getToken } = useAuth();
  const [profil, setProfil] = useState<Profil | null>(null);
  const [apiError, setApiError] = useState("");
  const [chargementProfil, setChargementProfil] = useState(true);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user]);

  useEffect(() => {
    async function fetchProfil() {
      if (!user) return;
      try {
        const token = await getToken();
        const res = await fetch(`${API_URL}/users/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Erreur API");
        const data = await res.json();
        setProfil(data);
      } catch {
        setApiError("Impossible de joindre cme-client-api.");
      } finally {
        setChargementProfil(false);
      }
    }
    fetchProfil();
  }, [user]);

  if (loading || !user) {
    return (
      <View style={styles.centre}>
        <ActivityIndicator size="large" color="#16a34a" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.titre}>✓ Connexion réussie</Text>
      <Text style={styles.soustitre}>
        Sprint 1 validé : Expo ↔ Firebase Auth ↔ cme-client-api
      </Text>

      <View style={styles.carte}>
        <Text style={styles.label}>Compte Firebase</Text>
        <Text style={styles.valeur}>{user.email}</Text>

        <Text style={[styles.label, { marginTop: 16 }]}>
          Profil renvoyé par cme-client-api
        </Text>
        {chargementProfil ? (
          <ActivityIndicator style={{ marginTop: 8 }} />
        ) : apiError ? (
          <Text style={styles.erreur}>{apiError}</Text>
        ) : (
          <Text style={styles.valeur}>
            {profil?.prenom} {profil?.nom} — {profil?.email}
          </Text>
        )}
      </View>

      <TouchableOpacity style={styles.boutonDeco} onPress={() => logout()}>
        <Text style={styles.boutonDecoTexte}>Se déconnecter</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  centre: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#fff" },
  container: { flex: 1, backgroundColor: "#f9fafb", padding: 24, paddingTop: 80 },
  titre: { fontSize: 22, fontWeight: "700", color: "#16a34a" },
  soustitre: { fontSize: 13, color: "#6b7280", marginTop: 4, marginBottom: 24 },
  carte: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 20,
    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  label: { fontSize: 12, color: "#9ca3af", textTransform: "uppercase", fontWeight: "600" },
  valeur: { fontSize: 15, color: "#111827", marginTop: 4 },
  erreur: { fontSize: 13, color: "#dc2626", marginTop: 4 },
  boutonDeco: { marginTop: 24, alignItems: "center", padding: 12 },
  boutonDecoTexte: { color: "#dc2626", fontWeight: "600", fontSize: 14 },
});
