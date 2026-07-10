import { request } from "./client";
import type {
  BookmarkCreateInput,
  BookmarkPage,
  BookmarkRead,
  BookmarkUpdateInput,
  ListBookmarksParams,
} from "./types";

export async function listBookmarks(params: ListBookmarksParams = {}): Promise<BookmarkPage> {
  const search = new URLSearchParams();
  if (params.tag) search.set("tag", params.tag);
  if (params.q) search.set("q", params.q);
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  if (params.offset !== undefined) search.set("offset", String(params.offset));

  const qs = search.toString();
  return request<BookmarkPage>(`/bookmarks${qs ? `?${qs}` : ""}`);
}

export async function createBookmark(input: BookmarkCreateInput): Promise<BookmarkRead> {
  return request<BookmarkRead>("/bookmarks", { method: "POST", body: input });
}

export async function getBookmark(id: string): Promise<BookmarkRead> {
  return request<BookmarkRead>(`/bookmarks/${id}`);
}

export async function updateBookmark(
  id: string,
  input: BookmarkUpdateInput
): Promise<BookmarkRead> {
  return request<BookmarkRead>(`/bookmarks/${id}`, { method: "PATCH", body: input });
}

export async function deleteBookmark(id: string): Promise<void> {
  await request<void>(`/bookmarks/${id}`, { method: "DELETE" });
}
