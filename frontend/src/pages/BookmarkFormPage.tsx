import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import * as bookmarksApi from "../api/bookmarks";
import { ApiError } from "../api/client";

export function BookmarkFormPage() {
  const { id } = useParams<{ id?: string }>();
  const isEditing = Boolean(id);
  const navigate = useNavigate();

  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(isEditing);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    bookmarksApi
      .getBookmark(id)
      .then((bookmark) => {
        if (cancelled) return;
        setUrl(bookmark.url);
        setTitle(bookmark.title);
        setDescription(bookmark.description ?? "");
        setTags(bookmark.tags.join(", "));
      })
      .catch(() => {
        if (!cancelled) setError("Couldn't load this bookmark.");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const tagList = tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    try {
      if (id) {
        await bookmarksApi.updateBookmark(id, {
          url,
          title,
          description: description || null,
          tags: tagList,
        });
      } else {
        await bookmarksApi.createBookmark({
          url,
          title,
          description: description || null,
          tags: tagList,
        });
      }
      await navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return <p>Loading...</p>;
  }

  return (
    <div className="bookmark-form-page">
      <h1>{isEditing ? "Edit bookmark" : "New bookmark"}</h1>
      <form onSubmit={(e) => void handleSubmit(e)}>
        <label>
          URL
          <input type="url" value={url} onChange={(e) => setUrl(e.target.value)} required />
        </label>
        <label>
          Title
          <input value={title} onChange={(e) => setTitle(e.target.value)} required />
        </label>
        <label>
          Description
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        <label>
          Tags (comma-separated)
          <input value={tags} onChange={(e) => setTags(e.target.value)} />
        </label>
        {error && (
          <p role="alert" className="form-error">
            {error}
          </p>
        )}
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Saving..." : "Save"}
        </button>
      </form>
    </div>
  );
}
