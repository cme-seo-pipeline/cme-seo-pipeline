interface WPPost {
  id: number;
  title: { rendered: string };
  link: string;
  date: string;
}

interface WPCategory {
  id: number;
  slug: string;
}

const SILOS = [
  { slug: "gaz", label: "🔥 Gaz", color: "border-blue-200" },
  { slug: "electricite", label: "⚡ Électricité", color: "border-yellow-200" },
  { slug: "renovation-energetique", label: "🏗️ Rénovation Énergétique", color: "border-purple-200" },
  { slug: "aide-energetique", label: "🏠 Aide Énergétique", color: "border-amber-200" },
  { slug: "solaire", label: "☀️ Solaire", color: "border-green-200" },
];

async function getSiloPosts(slug: string): Promise<WPPost[]> {
  try {
    const catRes = await fetch(
      `https://www.comprendre-mon-energie.fr/wp-json/wp/v2/categories?slug=${slug}`,
      { next: { revalidate: 3600 } }
    );
    if (!catRes.ok) return [];
    const cats: WPCategory[] = await catRes.json();
    if (!cats.length) return [];

    const postsRes = await fetch(
      `https://www.comprendre-mon-energie.fr/wp-json/wp/v2/posts?categories=${cats[0].id}&per_page=4&orderby=date&order=desc`,
      { next: { revalidate: 3600 } }
    );
    if (!postsRes.ok) return [];
    return postsRes.json();
  } catch {
    return [];
  }
}

export default async function EnergiePage() {
  const resultats = await Promise.all(
    SILOS.map(async (silo) => ({
      ...silo,
      posts: await getSiloPosts(silo.slug),
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
            <h2 className="font-bold text-gray-900 mb-3">{silo.label}</h2>
            {silo.posts.length === 0 ? (
              <p className="text-sm text-gray-400">
                Aucun article disponible pour le moment.
              </p>
            ) : (
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
