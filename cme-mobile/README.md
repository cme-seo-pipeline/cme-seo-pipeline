# CME Espace Client — Mobile (Sprint 1)

Application React Native (Expo) — meme backend que l'espace client web
(`cme-client-api` + Firebase Auth). Objectif Sprint 1 : valider la chaine
compte -> connexion -> appel API reelle, avant de construire le reste
des ecrans.

## Mise en route (depuis Cloud Shell)

```bash
cd ~/cme-pipeline
mkdir -p cme-mobile
# (deposer ici tous les fichiers telecharges)
cd cme-mobile

npm install

cp .env.example .env.local
# Completer EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET avec la meme valeur
# que dans espace-client/.env (ou cloudbuild.yaml)
```

## Lancer en developpement

```bash
npx expo start
```

Un QR code s'affiche dans le terminal. Installez l'app **Expo Go**
(gratuite, App Store / Play Store) sur votre telephone, scannez le QR
code — l'app se lance directement sur votre appareil, sans build
native, sans Android Studio.

## Validation Sprint 1

1. Ouvrir l'app -> redirige vers l'ecran de connexion
2. Se connecter avec un compte existant de l'espace client web
   (meme email/mot de passe, meme projet Firebase)
3. Si la connexion reussit, l'ecran d'accueil doit afficher :
   - Le compte Firebase connecte
   - Le profil renvoye par `cme-client-api` (`/users/me`)

Si les deux informations s'affichent, toute la chaine
**Expo <-> Firebase Auth <-> cme-client-api** est validee et le
Sprint 2 (ecrans complets : dossiers, profil, energie) peut commencer.

## Build Android pour Google Play (plus tard, une fois le compte
developpeur ouvert - 25$ one-time, console.play.google.com)

```bash
npm install -g eas-cli
eas login
eas build:configure
eas build --platform android --profile preview
```

Ce build se fait entierement dans le cloud (EAS Build) — pas besoin
d'Android Studio installe localement.
