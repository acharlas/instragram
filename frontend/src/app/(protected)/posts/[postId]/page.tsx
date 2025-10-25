type PostPageProps = { params: Promise<{ postId: string }> };

export default async function PostDetailPage({ params }: PostPageProps) {
  const { postId } = await params;
  void postId;
  return null;
}
