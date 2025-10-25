export type FeedPost = {
  id: number;
  author_id: string;
  author_name: string | null;
  image_key: string;
  caption: string | null;
};

export type FeedResponse = FeedPost[];
