import { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from "react-native";
import { router } from "expo-router";
import { useAuth } from "../contexts/AuthContext";

export default function LoginScreen() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [erreur, setErreur] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin() {
    setErreur("");
    setLoading(true);
    try {
      await login(email, password);
      router.replace("/");
    } catch {
      setErreur("Email ou mot de passe incorrect.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      style={styles.container}
    >
      <View style={styles.card}>
        <Text style={styles.title}>Connexion</Text>
        <Text style={styles.subtitle}>Comprendre Mon Énergie</Text>

        <TextInput
          style={styles.input}
          placeholder="Email"
          placeholderTextColor="#9ca3af"
          autoCapitalize="none"
          keyboardType="email-address"
          value={email}
          onChangeText={setEmail}
        />
        <TextInput
          style={styles.input}
          placeholder="Mot de passe"
          placeholderTextColor="#9ca3af"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
        />

        <TouchableOpacity
          style={styles.lienMdp}
          onPress={() => router.push("/forgot-password")}
        >
          <Text style={styles.lienMdpTexte}>Mot de passe oublié ?</Text>
        </TouchableOpacity>

        {erreur ? <Text style={styles.erreur}>{erreur}</Text> : null}

        <TouchableOpacity
          style={styles.bouton}
          onPress={handleLogin}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.boutonTexte}>Se connecter</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.lienInscription}
          onPress={() => router.push("/register")}
        >
          <Text style={styles.lienInscriptionTexte}>
            Pas encore de compte ? Créer un compte
          </Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f9fafb",
    justifyContent: "center",
    padding: 24,
  },
  card: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 24,
    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  title: { fontSize: 24, fontWeight: "700", color: "#111827" },
  subtitle: { fontSize: 14, color: "#6b7280", marginBottom: 24 },
  input: {
    height: 48,
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 10,
    paddingHorizontal: 14,
    marginBottom: 12,
    fontSize: 15,
    color: "#111827",
    backgroundColor: "#fff",
  },
  lienMdp: { alignItems: "flex-end", marginBottom: 4 },
  lienMdpTexte: { color: "#16a34a", fontSize: 12, fontWeight: "600" },
  erreur: {
    color: "#dc2626",
    backgroundColor: "#fef2f2",
    borderWidth: 1,
    borderColor: "#fecaca",
    borderRadius: 8,
    padding: 10,
    fontSize: 13,
    marginTop: 8,
    marginBottom: 12,
  },
  bouton: {
    height: 48,
    backgroundColor: "#16a34a",
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 8,
  },
  boutonTexte: { color: "#fff", fontWeight: "600", fontSize: 15 },
  lienInscription: { marginTop: 16, alignItems: "center" },
  lienInscriptionTexte: { color: "#16a34a", fontWeight: "600", fontSize: 13 },
});
