interface WPPost {
  id: number;
  title: { rendered: string };
  link: string;
  date: string;
}

interface WPCategory {
  id: number;
  slug: string;
  link: string;
}

const SILOS = [
  { slug: "gaz", label: "🔥 Gaz", color: "border-blue-200" },
  { slug: "electricite", label: "⚡ Électricité", color: "border-yellow-200" },
  { slug: "renovation-energetique", label: "🏗️ Rénovation Énergétique", color: "border-purple-200" },
  { slug: "aide-energetique", label: "🏠 Aide Énergétique", color: "border-amber-200" },
  { slug: "solaire", label: "☀️ Solaire", color: "border-green-200" },
];

async function getSiloData(slug: string): Promise<{ posts: WPPost[]; lienSilo: string | null }> {
  try {
    // 1. Trouver la categorie "silo" (parente) et recuperer son lien
    const catRes = await fetch(
      `https://www.comprendre-mon-energie.fr/wp-json/wp/v2/categories?slug=${slug}`,
      { next: { revalidate: 3600 } }
    );
    if (!catRes.ok) return { posts: [], lienSilo: null };
    const cats: WPCategory[] = await catRes.json();
    if (!cats.length) return { posts: [], lienSilo: null };
    const siloId = cats[0].id;
    const lienSilo = cats[0].link;

    // 2. Les silos sont des categories parentes SANS articles directs —
    //    les vrais articles sont rattaches aux sous-categories (sous-silos).
    //    On recupere donc les enfants du silo.
    const enfantsRes = await fetch(
      `https://www.comprendre-mon-energie.fr/wp-json/wp/v2/categories?parent=${siloId}&per_page=50`,
      { next: { revalidate: 3600 } }
    );
    const enfants: WPCategory[] = enfantsRes.ok ? await enfantsRes.json() : [];
    const idsRecherche = [siloId, ...enfants.map((e) => e.id)].join(",");

    // 3. Articles les plus recents, tous sous-silos confondus
    const postsRes = await fetch(
      `https://www.comprendre-mon-energie.fr/wp-json/wp/v2/posts?categories=${idsRecherche}&per_page=4&orderby=date&order=desc`,
      { next: { revalidate: 3600 } }
    );
    const posts = postsRes.ok ? await postsRes.json() : [];
    return { posts, lienSilo };
  } catch {
    return { posts: [], lienSilo: null };
  }
}

export default async function EnergiePage() {
  const resultats = await Promise.all(
    SILOS.map(async (silo) => ({
      ...silo,
      ...(await getSiloData(silo.slug)),
    }))
  );

  return (
    <div className="flex-1 max-w-5xl w-full mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Énergie</h1>
        <p className="text-sm text-gray-500">
          Guides et actualités par domaine
        </p>
      </div>

      <div className="space-y-6">
        {resultats.map((silo) => (
          <div
            key={silo.slug}
            className={`bg-white rounded-2xl border-2 ${silo.color} p-5`}
          >
            {silo.lienSilo ? (
              <a
                href={silo.lienSilo}
                target="_blank"
                rel="noopener noreferrer"
                className={`inline-flex items-center gap-1 font-bold text-gray-900 hover:text-green-600 transition-colors ${
                  silo.posts.length > 0 ? "mb-3" : ""
                }`}
              >
                {silo.label}
                <span className="text-sm">→</span>
              </a>
            ) : (
              <h2 className={`font-bold text-gray-900 ${silo.posts.length > 0 ? "mb-3" : ""}`}>
                {silo.label}
              </h2>
            )}

            {silo.posts.length > 0 && (
              <ul className="space-y-2">
                {silo.posts.map((post) => (
                  <li key={post.id}>
                    <a
                      href={post.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-gray-700 hover:text-green-600 transition-colors"
                      dangerouslySetInnerHTML={{ __html: post.title.rendered }}
                    />
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
