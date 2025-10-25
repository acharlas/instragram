export type FeedPost = {
  id: number;
  author_id: string;
  image_key: string;
  caption: string | null;
};

export type FeedResponse = FeedPost[];
