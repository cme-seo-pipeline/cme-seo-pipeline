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

interface PageProps {
  searchParams: Promise<{ page?: string }>;
}

const PAR_PAGE = 30;

async function getPosts(page: number): Promise<{ posts: WPPost[]; totalPages: number }> {
  try {
    const res = await fetch(
      `https://www.comprendre-mon-energie.fr/wp-json/wp/v2/posts?per_page=${PAR_PAGE}&page=${page}&orderby=date&order=desc&_embed`,
      { next: { revalidate: 3600 } }
    );
    if (!res.ok) return { posts: [], totalPages: 1 };
    const posts = await res.json();
    const totalPages = parseInt(res.headers.get("X-WP-TotalPages") || "1", 10);
    return { posts, totalPages };
  } catch {
    return { posts: [], totalPages: 1 };
  }
}

function nettoyerExtrait(html: string): string {
  return html.replace(/<[^>]+>/g, "").trim().slice(0, 160);
}

export default async function NewsPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const pageActuelle = Math.max(1, parseInt(params.page || "1", 10));
  const { posts, totalPages } = await getPosts(pageActuelle);

  return (
    <div className="flex-1 max-w-5xl w-full mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">News</h1>
        <p className="text-sm text-gray-500">
          Tous les articles, les plus récents en premier
        </p>
      </div>

      {posts.length === 0 ? (
        <p className="text-gray-500 text-center py-12">
          Aucun article disponible pour le moment.
        </p>
      ) : (
        <>
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
                    <img src={image} alt="" className="w-full h-40 object-cover" />
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

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              {pageActuelle > 1 && (
                <a
                  href={`/news?page=${pageActuelle - 1}`}
                  className="h-10 px-4 flex items-center rounded-lg border border-gray-300 bg-white text-sm text-gray-700 hover:bg-gray-50"
                >
                  ← Précédent
                </a>
              )}
              <span className="text-sm text-gray-500 px-3">
                Page {pageActuelle} / {totalPages}
              </span>
              {pageActuelle < totalPages && (
                <a
                  href={`/news?page=${pageActuelle + 1}`}
                  className="h-10 px-4 flex items-center rounded-lg border border-gray-300 bg-white text-sm text-gray-700 hover:bg-gray-50"
                >
                  Suivant →
                </a>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
