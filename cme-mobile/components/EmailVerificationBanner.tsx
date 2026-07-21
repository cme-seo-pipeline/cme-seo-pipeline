import { useState } from "react";
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from "react-native";
import { useAuth } from "../contexts/AuthContext";

export default function EmailVerificationBanner() {
  const { user, emailVerified, resendVerification, refreshEmailStatus } = useAuth();
  const [envoiEnCours, setEnvoiEnCours] = useState(false);
  const [rafraichissementEnCours, setRafraichissementEnCours] = useState(false);
  const [message, setMessage] = useState("");

  if (!user || emailVerified) return null;

  async function handleResend() {
    setEnvoiEnCours(true);
    setMessage("");
    try {
      await resendVerification();
      setMessage("Email renvoyé !");
    } catch {
      setMessage("Erreur, réessayez.");
    } finally {
      setEnvoiEnCours(false);
    }
  }

  async function handleRefresh() {
    setRafraichissementEnCours(true);
    setMessage("");
    try {
      await refreshEmailStatus();
    } finally {
      setRafraichissementEnCours(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.texte} numberOfLines={2}>
        📧 Vérifiez votre email — lien envoyé à {user.email}
        {message ? ` · ${message}` : ""}
      </Text>
      <View style={styles.boutons}>
        <TouchableOpacity
          style={styles.bouton}
          onPress={handleRefresh}
          disabled={rafraichissementEnCours}
        >
          {rafraichissementEnCours ? (
            <ActivityIndicator size="small" color="#92400e" />
          ) : (
            <Text style={styles.boutonTexte}>J&apos;ai vérifié</Text>
          )}
        </TouchableOpacity>
        <TouchableOpacity onPress={handleResend} disabled={envoiEnCours}>
          <Text style={styles.lien}>{envoiEnCours ? "Envoi..." : "Renvoyer"}</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#fffbeb",
    borderBottomWidth: 1,
    borderBottomColor: "#fde68a",
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  texte: { fontSize: 12, color: "#92400e" },
  boutons: { flexDirection: "row", alignItems: "center", gap: 12, marginTop: 8 },
  bouton: {
    backgroundColor: "#fef3c7",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  boutonTexte: { fontSize: 11, fontWeight: "600", color: "#92400e" },
  lien: { fontSize: 11, fontWeight: "600", color: "#b45309", textDecorationLine: "underline" },
});
