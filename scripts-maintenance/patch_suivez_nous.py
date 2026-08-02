FICHIER = "cme-mobile/app/(tabs)/profil.tsx"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH 1 — Imports (Image, Linking)
# ============================================================
ancien1 = '''import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  ScrollView,
} from "react-native";'''

nouveau1 = '''import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  ScrollView,
  Image,
  Linking,
} from "react-native";'''

if ancien1 not in contenu:
    print("❌ PATCH 1 (imports) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien1, nouveau1, 1)
    print("✅ PATCH 1 (imports) : Image + Linking ajoutes")

# ============================================================
# PATCH 2 — Constantes (logo + liste des reseaux)
# ============================================================
ancien2 = '''const API_URL = process.env.EXPO_PUBLIC_CLIENT_API_URL;'''

nouveau2 = ancien2 + '''
const LOGO_URL =
  "https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/03/cropped-logo-officiel-comprendre-mon-energie-observatoire.png";
const RESEAUX = [
  {
    nom: "Facebook",
    image: "https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/07/Facebook_logo_comprendre-mon-energie.png",
    lien: "https://web.facebook.com/people/Comprendre-Mon-%C3%89nergie/61592180973793/",
  },
  {
    nom: "Instagram",
    image: "https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/08/image_instagram.png",
    lien: "https://www.instagram.com/cme262026/",
  },
  {
    nom: "LinkedIn",
    image: "https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/05/icone-linkedin-comprendre-mon-energie.jpg",
    lien: "https://www.linkedin.com/company/comprendre-mon-energie/",
  },
  {
    nom: "Notre site web",
    image: LOGO_URL,
    lien: "https://www.comprendre-mon-energie.fr/",
  },
];'''

if "const RESEAUX" in contenu:
    print("⏭️  PATCH 2 (constantes reseaux) : deja present, ignore")
elif ancien2 not in contenu:
    print("❌ PATCH 2 (constantes reseaux) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien2, nouveau2, 1)
    print("✅ PATCH 2 (constantes reseaux) : ajoutees")

# ============================================================
# PATCH 3 — JSX : nouvelle carte "Suivez-nous"
# ============================================================
ancien3 = '''        <TouchableOpacity style={styles.bouton} onPress={handleSave} disabled={sauvegarde}>
          {sauvegarde ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.boutonTexte}>Enregistrer</Text>
          )}
        </TouchableOpacity>
      </View>
      <View style={styles.carte}>
        <Text style={styles.sectionTitre}>Sécurité</Text>'''

nouveau3 = '''        <TouchableOpacity style={styles.bouton} onPress={handleSave} disabled={sauvegarde}>
          {sauvegarde ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.boutonTexte}>Enregistrer</Text>
          )}
        </TouchableOpacity>
      </View>
      <View style={styles.carte}>
        <Text style={styles.sectionTitre}>Suivez-nous</Text>
        <Text style={styles.sectionSousTitre}>
          Restez informé de nos actualités sur tous nos canaux
        </Text>
        {RESEAUX.map((reseau, index) => (
          <TouchableOpacity
            key={reseau.nom}
            style={[
              styles.ligneReseau,
              index === RESEAUX.length - 1 && { borderBottomWidth: 0 },
            ]}
            onPress={() => Linking.openURL(reseau.lien)}
          >
            <Image source={{ uri: reseau.image }} style={styles.iconeReseau} />
            <Text style={styles.texteReseau}>{reseau.nom}</Text>
            <Text style={styles.chevronReseau}>›</Text>
          </TouchableOpacity>
        ))}
      </View>
      <View style={styles.carte}>
        <Text style={styles.sectionTitre}>Sécurité</Text>'''

if "Suivez-nous" in contenu:
    print("⏭️  PATCH 3 (carte Suivez-nous) : deja present, ignore")
elif ancien3 not in contenu:
    print("❌ PATCH 3 (carte Suivez-nous) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien3, nouveau3, 1)
    print("✅ PATCH 3 (carte Suivez-nous) : ajoutee")

# ============================================================
# PATCH 4 — Styles pour la liste des reseaux
# ============================================================
ancien4 = '''  label: { fontSize: 12, color: "#6b7280", fontWeight: "600", marginBottom: 6, marginTop: 12 },'''

nouveau4 = ancien4 + '''
  ligneReseau: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#f3f4f6",
  },
  iconeReseau: { width: 32, height: 32, borderRadius: 8, marginRight: 12 },
  texteReseau: { flex: 1, fontSize: 15, color: "#111827", fontWeight: "500" },
  chevronReseau: { fontSize: 20, color: "#d1d5db" },'''

if "ligneReseau:" in contenu:
    print("⏭️  PATCH 4 (styles reseaux) : deja present, ignore")
elif ancien4 not in contenu:
    print("❌ PATCH 4 (styles reseaux) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien4, nouveau4, 1)
    print("✅ PATCH 4 (styles reseaux) : ajoutes")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
