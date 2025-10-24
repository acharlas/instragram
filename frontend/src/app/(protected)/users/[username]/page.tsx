type UserProfilePageProps = { params: Promise<{ username: string }> };

export default async function UserProfilePage({ params }: UserProfilePageProps) {
  const { username } = await params;
  void username;
  return null;
}
