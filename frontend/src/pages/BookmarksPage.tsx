import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import * as bookmarksApi from "../api/bookmarks";
import type { BookmarkRead } from "../api/types";
import { useAuth } from "../auth/useAuth";

const PAGE_SIZE = 10;

export function BookmarksPage() {
  const { logout } = useAuth();
  const [items, setItems] = useState<BookmarkRead[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [tag, setTag] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    bookmarksApi
      .listBookmarks({ q: search || undefined, tag: tag || undefined, limit: PAGE_SIZE, offset })
      .then((page) => {
        if (cancelled) return;
        setItems(page.items);
        setTotal(page.total);
      })
      .catch(() => {
        if (!cancelled) setError("Couldn't load bookmarks.");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [search, tag, offset]);

  async function handleDelete(id: string): Promise<void> {
    await bookmarksApi.deleteBookmark(id);
    setItems((current) => current.filter((bookmark) => bookmark.id !== id));
    setTotal((current) => current - 1);
  }

  const hasNextPage = offset + PAGE_SIZE < total;
  const hasPrevPage = offset > 0;

  return (
    <div className="bookmarks-page">
      <header>
        <h1>Bookmarks</h1>
        <button type="button" onClick={() => void logout()}>
          Log out
        </button>
      </header>

      <div className="filters">
        <input
          placeholder="Search title, url, description"
          value={search}
          onChange={(e) => {
            setOffset(0);
            setSearch(e.target.value);
          }}
        />
        <input
          placeholder="Filter by tag"
          value={tag}
          onChange={(e) => {
            setOffset(0);
            setTag(e.target.value);
          }}
        />
        <Link to="/bookmarks/new">+ New bookmark</Link>
      </div>

      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}

      {isLoading ? (
        <p>Loading...</p>
      ) : items.length === 0 ? (
        <p>No bookmarks yet.</p>
      ) : (
        <ul className="bookmark-list">
          {items.map((bookmark) => (
            <li key={bookmark.id}>
              <a href={bookmark.url} target="_blank" rel="noreferrer">
                {bookmark.title}
              </a>
              {bookmark.tags.length > 0 && <span className="tags">{bookmark.tags.join(", ")}</span>}
              <Link to={`/bookmarks/${bookmark.id}/edit`}>Edit</Link>
              <button type="button" onClick={() => void handleDelete(bookmark.id)}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="pagination">
        <button
          type="button"
          disabled={!hasPrevPage}
          onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}
        >
          Previous
        </button>
        <span>{total} total</span>
        <button
          type="button"
          disabled={!hasNextPage}
          onClick={() => setOffset((current) => current + PAGE_SIZE)}
        >
          Next
        </button>
      </div>
    </div>
  );
}
