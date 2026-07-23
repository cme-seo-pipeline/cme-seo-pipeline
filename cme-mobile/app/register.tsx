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
  ScrollView,
  Linking,
} from "react-native";
import { router } from "expo-router";
import { useAuth } from "../contexts/AuthContext";
import PasswordInput from "../components/PasswordInput";

export default function RegisterScreen() {
  const { register } = useAuth();
  const [prenom, setPrenom] = useState("");
  const [nom, setNom] = useState("");
  const [email, setEmail] = useState("");
  const [telephone, setTelephone] = useState("");
  const [password, setPassword] = useState("");
  const [accepteCgu, setAccepteCgu] = useState(false);
  const [erreur, setErreur] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleRegister() {
    setErreur("");
    if (!prenom.trim() || !nom.trim() || !email.trim() || !telephone.trim()) {
      setErreur("Merci de remplir tous les champs.");
      return;
    }
    if (password.length < 6) {
      setErreur("Le mot de passe doit contenir au moins 6 caractères.");
      return;
    }
    if (!accepteCgu) {
      setErreur("Merci d'accepter les conditions générales pour continuer.");
      return;
    }
    setLoading(true);
    try {
      await register({
        prenom: prenom.trim(),
        nom: nom.trim(),
        email: email.trim(),
        telephone: telephone.trim(),
        password,
      });
      router.replace("/");
    } catch (err) {
      setErreur(err instanceof Error ? err.message : "Erreur lors de l'inscription.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: "center", padding: 24 }}>
        <View style={styles.card}>
          <Text style={styles.title}>Créer un compte</Text>
          <Text style={styles.subtitle}>Comprendre Mon Énergie</Text>

          <View style={styles.row}>
            <TextInput
              style={[styles.input, styles.inputHalf]}
              placeholder="Prénom"
              placeholderTextColor="#9ca3af"
              value={prenom}
              onChangeText={setPrenom}
            />
            <TextInput
              style={[styles.input, styles.inputHalf]}
              placeholder="Nom"
              placeholderTextColor="#9ca3af"
              value={nom}
              onChangeText={setNom}
            />
          </View>

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
            placeholder="Téléphone"
            placeholderTextColor="#9ca3af"
            keyboardType="phone-pad"
            value={telephone}
            onChangeText={setTelephone}
          />
          <PasswordInput
            containerStyle={{ marginBottom: 12 }}
            style={styles.input}
            placeholder="Mot de passe (6 caractères min.)"
            placeholderTextColor="#9ca3af"
            value={password}
            onChangeText={setPassword}
          />

          <TouchableOpacity
            style={styles.cguRow}
            onPress={() => setAccepteCgu((v) => !v)}
            activeOpacity={0.7}
          >
            <View style={[styles.checkbox, accepteCgu && styles.checkboxCoche]}>
              {accepteCgu ? <Text style={styles.checkboxCoche2}>✓</Text> : null}
            </View>
            <Text style={styles.cguTexte}>
              J&apos;accepte les{" "}
              <Text
                style={styles.cguLien}
                onPress={() =>
                  Linking.openURL(
                    "https://www.comprendre-mon-energie.fr/cadre-legal-et-confidentialite/"
                  )
                }
              >
                conditions générales et la politique de confidentialité
              </Text>
            </Text>
          </TouchableOpacity>

          {erreur ? <Text style={styles.erreur}>{erreur}</Text> : null}

          <TouchableOpacity style={styles.bouton} onPress={handleRegister} disabled={loading}>
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.boutonTexte}>Créer mon compte</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity style={styles.lienConnexion} onPress={() => router.back()}>
            <Text style={styles.lienConnexionTexte}>Déjà un compte ? Se connecter</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb" },
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
  subtitle: { fontSize: 14, color: "#6b7280", marginBottom: 20 },
  row: { flexDirection: "row", gap: 10 },
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
  inputHalf: { flex: 1 },
  cguRow: { flexDirection: "row", alignItems: "flex-start", gap: 10, marginTop: 4, marginBottom: 8 },
  checkbox: {
    width: 20,
    height: 20,
    borderRadius: 5,
    borderWidth: 1.5,
    borderColor: "#d1d5db",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 1,
  },
  checkboxCoche: { backgroundColor: "#16a34a", borderColor: "#16a34a" },
  checkboxCoche2: { color: "#fff", fontSize: 13, fontWeight: "700" },
  cguTexte: { flex: 1, fontSize: 13, color: "#6b7280", lineHeight: 18 },
  cguLien: { color: "#16a34a", fontWeight: "600" },
  erreur: {
    color: "#dc2626",
    backgroundColor: "#fef2f2",
    borderWidth: 1,
    borderColor: "#fecaca",
    borderRadius: 8,
    padding: 10,
    fontSize: 13,
    marginBottom: 12,
  },
  bouton: {
    height: 48,
    backgroundColor: "#16a34a",
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 4,
  },
  boutonTexte: { color: "#fff", fontWeight: "600", fontSize: 15 },
  lienConnexion: { marginTop: 16, alignItems: "center" },
  lienConnexionTexte: { color: "#16a34a", fontWeight: "600", fontSize: 13 },
});
