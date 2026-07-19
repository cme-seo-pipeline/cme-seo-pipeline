import { useState, useEffect } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  ScrollView,
} from "react-native";
import { router } from "expo-router";
import { useAuth } from "../../contexts/AuthContext";

const API_URL = process.env.EXPO_PUBLIC_CLIENT_API_URL;

interface Profil {
  prenom?: string;
  nom?: string;
  telephone?: string;
}

export default function ProfilScreen() {
  const { user, logout, getToken } = useAuth();
  const [profil, setProfil] = useState<Profil>({});
  const [loading, setLoading] = useState(true);
  const [sauvegarde, setSauvegarde] = useState(false);
  const [succes, setSucces] = useState(false);

  useEffect(() => {
    fetchProfil();
  }, []);

  async function fetchProfil() {
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/users/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setProfil(data);
    } catch {
      // silencieux
    } finally {
      setLoading(false);
    }
  }

  function update(champ: keyof Profil, valeur: string) {
    setProfil((p) => ({ ...p, [champ]: valeur }));
    setSucces(false);
  }

  async function handleSave() {
    setSauvegarde(true);
    setSucces(false);
    try {
      const token = await getToken();
      await fetch(`${API_URL}/users/me`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          prenom: profil.prenom,
          nom: profil.nom,
          telephone: profil.telephone,
        }),
      });
      setSucces(true);
    } catch {
      // silencieux
    } finally {
      setSauvegarde(false);
    }
  }

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  if (loading) {
    return (
      <View style={styles.centre}>
        <ActivityIndicator size="large" color="#16a34a" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 20, paddingTop: 60 }}>
      <Text style={styles.titre}>Mon profil</Text>

      <View style={styles.carte}>
        <Text style={styles.label}>Prénom</Text>
        <TextInput
          style={styles.input}
          value={profil.prenom || ""}
          onChangeText={(v) => update("prenom", v)}
        />

        <Text style={styles.label}>Nom</Text>
        <TextInput
          style={styles.input}
          value={profil.nom || ""}
          onChangeText={(v) => update("nom", v)}
        />

        <Text style={styles.label}>Email</Text>
        <View style={[styles.input, styles.inputDisabled]}>
          <Text style={{ color: "#9ca3af" }}>{user?.email}</Text>
        </View>

        <Text style={styles.label}>Téléphone</Text>
        <TextInput
          style={styles.input}
          value={profil.telephone || ""}
          onChangeText={(v) => update("telephone", v)}
          keyboardType="phone-pad"
        />

        {succes ? <Text style={styles.succes}>✓ Enregistré avec succès</Text> : null}

        <TouchableOpacity style={styles.bouton} onPress={handleSave} disabled={sauvegarde}>
          {sauvegarde ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.boutonTexte}>Enregistrer</Text>
          )}
        </TouchableOpacity>
      </View>

      <TouchableOpacity style={styles.boutonDeco} onPress={handleLogout}>
        <Text style={styles.boutonDecoTexte}>Se déconnecter</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  centre: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#fff" },
  container: { flex: 1, backgroundColor: "#f9fafb" },
  titre: { fontSize: 22, fontWeight: "700", color: "#111827", marginBottom: 16 },
  carte: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 20,
    shadowColor: "#000",
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 1,
  },
  label: { fontSize: 12, color: "#6b7280", fontWeight: "600", marginBottom: 6, marginTop: 12 },
  input: {
    height: 46,
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 10,
    paddingHorizontal: 12,
    fontSize: 15,
    color: "#111827",
    backgroundColor: "#fff",
    justifyContent: "center",
  },
  inputDisabled: { backgroundColor: "#f3f4f6" },
  succes: {
    color: "#15803d",
    backgroundColor: "#dcfce7",
    borderRadius: 8,
    padding: 10,
    fontSize: 13,
    marginTop: 16,
    textAlign: "center",
  },
  bouton: {
    height: 48,
    backgroundColor: "#16a34a",
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 20,
  },
  boutonTexte: { color: "#fff", fontWeight: "600", fontSize: 15 },
  boutonDeco: { marginTop: 20, alignItems: "center", padding: 12 },
  boutonDecoTexte: { color: "#dc2626", fontWeight: "600", fontSize: 14 },
});
