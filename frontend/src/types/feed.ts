export type FeedPost = {
  id: number;
  author_id: string;
  author_name: string | null;
  image_key: string;
  caption: string | null;
  like_count: number;
  viewer_has_liked: boolean;
};

export type FeedResponse = FeedPost[];
