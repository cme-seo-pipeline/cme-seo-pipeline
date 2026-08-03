FICHIER = "cme-mobile/app/(tabs)/assistance.tsx"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH 1 — Import ScrollView
# ============================================================
ancien1 = '''import { View, Text, TouchableOpacity, StyleSheet, Linking } from "react-native";'''
nouveau1 = '''import { View, Text, TouchableOpacity, StyleSheet, Linking, ScrollView } from "react-native";'''

if "ScrollView" in contenu.split("\n")[0]:
    print("⏭️  PATCH 1 (import ScrollView) : deja present, ignore")
elif ancien1 not in contenu:
    print("❌ PATCH 1 (import ScrollView) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien1, nouveau1, 1)
    print("✅ PATCH 1 (import ScrollView) : ajoute")

# ============================================================
# PATCH 2 — Racine : View -> ScrollView
# ============================================================
ancien2 = '''    <View style={styles.container}>
      <Text style={styles.titre}>Assistance</Text>'''
nouveau2 = '''    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.contenuScroll}
      showsVerticalScrollIndicator={false}
    >
      <Text style={styles.titre}>Assistance</Text>'''

if "contentContainerStyle={styles.contenuScroll}" in contenu:
    print("⏭️  PATCH 2 (ouverture ScrollView) : deja present, ignore")
elif ancien2 not in contenu:
    print("❌ PATCH 2 (ouverture ScrollView) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien2, nouveau2, 1)
    print("✅ PATCH 2 (ouverture ScrollView) : ajoutee")

# ============================================================
# PATCH 3 — Fermeture : </View> -> </ScrollView>
# ============================================================
ancien3 = '''        <Text style={styles.carteGuidesLien}>Consulter les guides →</Text>
      </TouchableOpacity>
    </View>
  );
}'''
nouveau3 = '''        <Text style={styles.carteGuidesLien}>Consulter les guides →</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}'''

if ancien3 not in contenu and "</ScrollView>\n  );\n}" in contenu:
    print("⏭️  PATCH 3 (fermeture ScrollView) : deja present, ignore")
elif ancien3 not in contenu:
    print("❌ PATCH 3 (fermeture ScrollView) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien3, nouveau3, 1)
    print("✅ PATCH 3 (fermeture ScrollView) : ajoutee")

# ============================================================
# PATCH 4 — Styles : deplacer le padding vers contentContainerStyle
# ============================================================
ancien4 = '''  container: { flex: 1, backgroundColor: "#f9fafb", paddingHorizontal: 16, paddingTop: 20 },'''
nouveau4 = '''  container: { flex: 1, backgroundColor: "#f9fafb" },
  contenuScroll: { paddingHorizontal: 16, paddingTop: 20, paddingBottom: 32 },'''

if "contenuScroll:" in contenu:
    print("⏭️  PATCH 4 (styles) : deja present, ignore")
elif ancien4 not in contenu:
    print("❌ PATCH 4 (styles) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien4, nouveau4, 1)
    print("✅ PATCH 4 (styles) : padding deplace vers contentContainerStyle")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
