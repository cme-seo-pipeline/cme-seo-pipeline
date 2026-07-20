import { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { useAuth } from "../../contexts/AuthContext";

const API_URL = process.env.EXPO_PUBLIC_CLIENT_API_URL;

const SUJETS = [
  { value: "solaire", label: "☀️ Panneaux solaires" },
  { value: "renovation", label: "🏗️ Rénovation énergétique" },
  { value: "aides", label: "🏠 Aides & subventions" },
  { value: "contrat", label: "⚡ Contrat gaz/électricité" },
  { value: "autre", label: "💬 Autre" },
];

export default function RendezVousScreen() {
  const { getToken } = useAuth();
  const [sujet, setSujet] = useState("");
  const [message, setMessage] = useState("");
  const [disponibilites, setDisponibilites] = useState("");
  const [envoye, setEnvoye] = useState(false);
  const [envoiEnCours, setEnvoiEnCours] = useState(false);
  const [erreur, setErreur] = useState("");

  async function handleSubmit() {
    if (!sujet || !message.trim()) {
      setErreur("Merci de choisir un sujet et de décrire votre besoin.");
      return;
    }
    setErreur("");
    setEnvoiEnCours(true);
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/leads`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          tool: "rendez-vous-expert",
          montant_estime: 0,
          economie_estimee: 0,
          details: { sujet, message: message.trim(), disponibilites: disponibilites.trim() },
        }),
      });
      if (!res.ok) throw new Error();
      setEnvoye(true);
    } catch {
      setErreur("Une erreur est survenue, merci de réessayer.");
    } finally {
      setEnvoiEnCours(false);
    }
  }

  function nouvelleDemande() {
    setEnvoye(false);
    setSujet("");
    setMessage("");
    setDisponibilites("");
  }

  if (envoye) {
    return (
      <View style={styles.centre}>
        <View style={styles.iconeOk}>
          <Text style={{ fontSize: 28 }}>✓</Text>
        </View>
        <Text style={styles.titreOk}>Demande envoyée !</Text>
        <Text style={styles.texteOk}>
          Un expert vous recontacte sous 48h pour convenir d&apos;un rendez-vous.
          {"\n"}Suivez cette demande dans l&apos;onglet Mes dossiers.
        </Text>
        <TouchableOpacity style={styles.boutonSecondaire} onPress={nouvelleDemande}>
          <Text style={styles.boutonSecondaireTexte}>Faire une nouvelle demande</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={{ padding: 20, paddingTop: 20, paddingBottom: 40 }}>
        <Text style={styles.titre}>Rendez-vous avec un expert</Text>
        <Text style={styles.soustitre}>
          Décrivez votre besoin, un conseiller vous recontacte pour fixer un créneau.
        </Text>

        <Text style={styles.label}>Sujet</Text>
        <View style={styles.chipsContainer}>
          {SUJETS.map((s) => (
            <TouchableOpacity
              key={s.value}
              style={[styles.chip, sujet === s.value && styles.chipActif]}
              onPress={() => setSujet(s.value)}
            >
              <Text style={[styles.chipTexte, sujet === s.value && styles.chipTexteActif]}>
                {s.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <Text style={styles.label}>Votre message</Text>
        <TextInput
          style={styles.textarea}
          multiline
          numberOfLines={4}
          placeholder="Décrivez votre projet ou votre question..."
          placeholderTextColor="#9ca3af"
          value={message}
          onChangeText={setMessage}
        />

        <Text style={styles.label}>Disponibilités (optionnel)</Text>
        <TextInput
          style={styles.input}
          placeholder="Ex : en semaine après 18h"
          placeholderTextColor="#9ca3af"
          value={disponibilites}
          onChangeText={setDisponibilites}
        />

        {erreur ? <Text style={styles.erreur}>{erreur}</Text> : null}

        <TouchableOpacity style={styles.bouton} onPress={handleSubmit} disabled={envoiEnCours}>
          {envoiEnCours ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.boutonTexte}>Envoyer ma demande</Text>
          )}
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb" },
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
  boutonSecondaire: { marginTop: 24, padding: 12 },
  boutonSecondaireTexte: { color: "#16a34a", fontWeight: "600", fontSize: 14 },
  titre: { fontSize: 22, fontWeight: "700", color: "#111827" },
  soustitre: { fontSize: 13, color: "#6b7280", marginTop: 4, marginBottom: 20 },
  label: { fontSize: 12, color: "#6b7280", fontWeight: "600", marginBottom: 8, marginTop: 16 },
  chipsContainer: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "#d1d5db",
    backgroundColor: "#fff",
  },
  chipActif: { backgroundColor: "#16a34a", borderColor: "#16a34a" },
  chipTexte: { fontSize: 13, color: "#374151", fontWeight: "500" },
  chipTexteActif: { color: "#fff" },
  textarea: {
    minHeight: 100,
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 10,
    padding: 12,
    fontSize: 15,
    color: "#111827",
    backgroundColor: "#fff",
    textAlignVertical: "top",
  },
  input: {
    height: 46,
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 10,
    paddingHorizontal: 12,
    fontSize: 15,
    color: "#111827",
    backgroundColor: "#fff",
  },
  erreur: {
    color: "#dc2626",
    backgroundColor: "#fef2f2",
    borderWidth: 1,
    borderColor: "#fecaca",
    borderRadius: 8,
    padding: 10,
    fontSize: 13,
    marginTop: 16,
  },
  bouton: {
    height: 48,
    backgroundColor: "#16a34a",
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 24,
  },
  boutonTexte: { color: "#fff", fontWeight: "600", fontSize: 15 },
});
