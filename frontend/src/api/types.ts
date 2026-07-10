export interface UserRead {
  id: string;
  email: string;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface BookmarkRead {
  id: string;
  url: string;
  title: string;
  description: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface BookmarkPage {
  items: BookmarkRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface BookmarkCreateInput {
  url: string;
  title: string;
  description?: string | null;
  tags?: string[];
}

export interface BookmarkUpdateInput {
  url?: string;
  title?: string;
  description?: string | null;
  tags?: string[];
}

export interface ListBookmarksParams {
  tag?: string;
  q?: string;
  limit?: number;
  offset?: number;
}
