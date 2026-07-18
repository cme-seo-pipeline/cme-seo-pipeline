interface WPPost {
  id: number;
  title: { rendered: string };
  excerpt: { rendered: string };
  link: string;
  date: string;
  _embedded?: {
    "wp:featuredmedia"?: Array<{ source_url: string }>;
  };
}

async function getLatestPosts(): Promise<WPPost[]> {
  try {
    const res = await fetch(
      "https://www.comprendre-mon-energie.fr/wp-json/wp/v2/posts?per_page=20&orderby=date&order=desc&_embed",
      { next: { revalidate: 3600 } } // cache 1h côté serveur
    );
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

function nettoyerExtrait(html: string): string {
  return html.replace(/<[^>]+>/g, "").trim().slice(0, 160);
}

export default async function NewsPage() {
  const posts = await getLatestPosts();

  return (
    <div className="flex-1 max-w-5xl w-full mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">News</h1>
        <p className="text-sm text-gray-500">
          Les derniers articles, mis à jour en continu
        </p>
      </div>

      {posts.length === 0 ? (
        <p className="text-gray-500 text-center py-12">
          Aucun article disponible pour le moment.
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {posts.map((post) => {
            const image = post._embedded?.["wp:featuredmedia"]?.[0]?.source_url;
            return (
              <a
                key={post.id}
                href={post.link}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-white rounded-2xl border border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
              >
                {image && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={image}
                    alt=""
                    className="w-full h-40 object-cover"
                  />
                )}
                <div className="p-4">
                  <p className="text-xs text-gray-400 mb-1">
                    {new Date(post.date).toLocaleDateString("fr-FR", {
                      day: "numeric",
                      month: "long",
                      year: "numeric",
                    })}
                  </p>
                  <h2
                    className="font-semibold text-gray-900 mb-2 leading-snug"
                    dangerouslySetInnerHTML={{ __html: post.title.rendered }}
                  />
                  <p className="text-sm text-gray-500 leading-relaxed">
                    {nettoyerExtrait(post.excerpt.rendered)}…
                  </p>
                </div>
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
}
