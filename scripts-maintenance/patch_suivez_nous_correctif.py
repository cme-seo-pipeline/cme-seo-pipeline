FICHIER = "cme-mobile/app/(tabs)/profil.tsx"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''        <TouchableOpacity style={styles.bouton} onPress={handleSave} disabled={sauvegarde}>
          {sauvegarde ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.boutonTexte}>Enregistrer</Text>
          )}
        </TouchableOpacity>
      </View>

      <View style={styles.carte}>
        <Text style={styles.sectionTitre}>Sécurité</Text>'''

nouveau = '''        <TouchableOpacity style={styles.bouton} onPress={handleSave} disabled={sauvegarde}>
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
    print("⏭️  PATCH (carte Suivez-nous) : deja present, ignore")
elif ancien not in contenu:
    print("❌ PATCH (carte Suivez-nous) : ancre TOUJOURS non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("✅ PATCH (carte Suivez-nous) : ajoutee cette fois")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
