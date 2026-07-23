import { View, Text, TouchableOpacity, StyleSheet, Linking } from "react-native";
import { router } from "expo-router";

export default function AssistanceScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.titre}>Assistance</Text>
      <Text style={styles.soustitre}>Une question ? Notre équipe vous répond.</Text>

      <TouchableOpacity
        style={styles.carte}
        onPress={() => Linking.openURL("mailto:contact@comprendre-mon-energie.fr")}
      >
        <Text style={styles.icone}>✉️</Text>
        <Text style={styles.carteTitre}>Par email</Text>
        <Text style={styles.carteTexte}>contact@comprendre-mon-energie.fr</Text>
        <Text style={styles.carteSousTexte}>Réponse sous 48h</Text>
      </TouchableOpacity>

      <View style={[styles.carte, styles.carteDesactivee]}>
        <Text style={styles.icone}>📞</Text>
        <Text style={styles.carteTitre}>Par téléphone</Text>
        <Text style={styles.carteTexteItalique}>Numéro à venir</Text>
        <Text style={styles.carteSousTexte}>Bientôt disponible</Text>
      </View>

      <TouchableOpacity
        style={styles.carte}
        onPress={() => router.push("/(tabs)/rendez-vous")}
      >
        <Text style={styles.icone}>📅</Text>
        <Text style={styles.carteTitre}>Parler à un expert</Text>
        <Text style={styles.carteTexte}>
          Prenez rendez-vous pour un accompagnement personnalisé
        </Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.carteGuides}
        onPress={() => Linking.openURL("https://www.comprendre-mon-energie.fr")}
      >
        <Text style={styles.carteGuidesTitre}>Besoin d&apos;un guide ?</Text>
        <Text style={styles.carteGuidesTexte}>
          Retrouvez tous nos articles sur le gaz, l&apos;électricité, le solaire et
          les aides à la rénovation sur notre site.
        </Text>
        <Text style={styles.carteGuidesLien}>Consulter les guides →</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb", paddingHorizontal: 16, paddingTop: 20 },
  titre: { fontSize: 22, fontWeight: "700", color: "#111827" },
  soustitre: { fontSize: 13, color: "#6b7280", marginTop: 4, marginBottom: 20 },
  carte: {
    backgroundColor: "#fff",
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    shadowColor: "#000",
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 1,
  },
  carteDesactivee: { opacity: 0.6 },
  icone: { fontSize: 24, marginBottom: 6 },
  carteTitre: { fontSize: 15, fontWeight: "600", color: "#111827", marginBottom: 4 },
  carteTexte: { fontSize: 13, color: "#6b7280" },
  carteTexteItalique: { fontSize: 13, color: "#9ca3af", fontStyle: "italic" },
  carteSousTexte: { fontSize: 11, color: "#9ca3af", marginTop: 2 },
  carteGuides: {
    backgroundColor: "#f0fdf4",
    borderRadius: 14,
    padding: 16,
    marginTop: 8,
  },
  carteGuidesTitre: { fontSize: 15, fontWeight: "700", color: "#166534", marginBottom: 6 },
  carteGuidesTexte: { fontSize: 13, color: "#15803d", lineHeight: 18 },
  carteGuidesLien: { fontSize: 13, fontWeight: "600", color: "#16a34a", marginTop: 10 },
});
