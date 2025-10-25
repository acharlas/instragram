import { getServerSession } from "next-auth";

import { authOptions } from "../../app/api/auth/[...nextauth]/route";

type SessionGetter = typeof getServerSession;

export function getSessionServer(getter: SessionGetter = getServerSession) {
  return getter(authOptions);
}
