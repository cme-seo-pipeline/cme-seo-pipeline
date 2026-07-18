export default function AssistancePage() {
  return (
    <div className="flex-1 max-w-2xl w-full mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Assistance</h1>
      <p className="text-sm text-gray-500 mb-8">
        Une question ? Notre équipe vous répond.
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        <a
          href="mailto:contact@comprendre-mon-energie.fr"
          className="bg-white rounded-2xl border border-gray-200 p-6 hover:shadow-md transition-shadow"
        >
          <div className="text-2xl mb-2">✉️</div>
          <h2 className="font-semibold text-gray-900 mb-1">Par email</h2>
          <p className="text-sm text-gray-500">
            contact@comprendre-mon-energie.fr
          </p>
          <p className="text-xs text-gray-400 mt-1">Réponse sous 48h</p>
        </a>

        <div className="bg-white rounded-2xl border border-gray-200 p-6 opacity-70">
          <div className="text-2xl mb-2">📞</div>
          <h2 className="font-semibold text-gray-900 mb-1">Par téléphone</h2>
          <p className="text-sm text-gray-400 italic">Numéro à venir</p>
          <p className="text-xs text-gray-400 mt-1">Bientôt disponible</p>
        </div>

        <a
          href="/rendez-vous"
          className="bg-white rounded-2xl border border-gray-200 p-6 hover:shadow-md transition-shadow sm:col-span-2"
        >
          <div className="text-2xl mb-2">📅</div>
          <h2 className="font-semibold text-gray-900 mb-1">
            Parler à un expert
          </h2>
          <p className="text-sm text-gray-500">
            Prenez rendez-vous pour un accompagnement personnalisé
          </p>
        </a>
      </div>

      <div className="mt-8 bg-gray-50 border border-gray-200 rounded-2xl p-6">
        <h2 className="font-semibold text-gray-900 mb-2">Questions fréquentes</h2>
        <p className="text-sm text-gray-500">
          Retrouvez nos guides détaillés dans la section{" "}
          <a href="/energie" className="text-green-600 font-medium hover:underline">
            Énergie
          </a>{" "}
          pour toutes vos questions sur le gaz, l&apos;électricité, le solaire
          et les aides à la rénovation.
        </p>
      </div>
    </div>
  );
}
