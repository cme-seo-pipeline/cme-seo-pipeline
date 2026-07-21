import { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { router } from "expo-router";
import { useAuth } from "../contexts/AuthContext";

export default function ForgotPasswordScreen() {
  const { resetPassword } = useAuth();
  const [email, setEmail] = useState("");
  const [envoye, setEnvoye] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit() {
    setLoading(true);
    try {
      await resetPassword(email);
    } catch {
      // Message volontairement generique : ne pas confirmer/infirmer
      // l'existence d'un compte pour cet email.
    } finally {
      setEnvoye(true);
      setLoading(false);
    }
  }

  if (envoye) {
    return (
      <View style={styles.centre}>
        <View style={styles.iconeOk}>
          <Text style={{ fontSize: 28 }}>✓</Text>
        </View>
        <Text style={styles.titreOk}>Email envoyé</Text>
        <Text style={styles.texteOk}>
          Si un compte existe avec l&apos;adresse {email}, vous recevrez un lien
          pour réinitialiser votre mot de passe.
        </Text>
        <TouchableOpacity style={styles.lien} onPress={() => router.replace("/login")}>
          <Text style={styles.lienTexte}>Retour à la connexion</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      style={styles.container}
    >
      <View style={styles.card}>
        <Text style={styles.title}>Mot de passe oublié</Text>
        <Text style={styles.subtitle}>
          Indiquez votre email, nous vous enverrons un lien de réinitialisation.
        </Text>

        <TextInput
          style={styles.input}
          placeholder="Email"
          placeholderTextColor="#9ca3af"
          autoCapitalize="none"
          keyboardType="email-address"
          value={email}
          onChangeText={setEmail}
        />

        <TouchableOpacity style={styles.bouton} onPress={handleSubmit} disabled={loading}>
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.boutonTexte}>Envoyer le lien</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity style={styles.lien} onPress={() => router.back()}>
          <Text style={styles.lienTexte}>Retour à la connexion</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb", justifyContent: "center", padding: 24 },
  centre: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#fff",
    padding: 32,
  },
  iconeOk: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: "#dcfce7",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 16,
  },
  titreOk: { fontSize: 20, fontWeight: "700", color: "#111827", marginBottom: 8 },
  texteOk: { fontSize: 14, color: "#6b7280", textAlign: "center", lineHeight: 20 },
  card: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 24,
    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  title: { fontSize: 22, fontWeight: "700", color: "#111827" },
  subtitle: { fontSize: 13, color: "#6b7280", marginTop: 4, marginBottom: 20 },
  input: {
    height: 48,
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 10,
    paddingHorizontal: 14,
    marginBottom: 16,
    fontSize: 15,
    color: "#111827",
    backgroundColor: "#fff",
  },
  bouton: {
    height: 48,
    backgroundColor: "#16a34a",
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
  },
  boutonTexte: { color: "#fff", fontWeight: "600", fontSize: 15 },
  lien: { marginTop: 20, alignItems: "center" },
  lienTexte: { color: "#16a34a", fontWeight: "600", fontSize: 13 },
});
