"use client";

import { useRouter } from "next/navigation";
import { signIn } from "next-auth/react";
import { useState } from "react";

export type CredentialsAuthenticator = typeof signIn;

export async function authenticateCredentials(
  username: string,
  password: string,
  authenticator: CredentialsAuthenticator = signIn,
) {
  try {
    const response = await authenticator("credentials", {
      username,
      password,
      redirect: false,
    });

    return Boolean(response && !response.error);
  } catch {
    return false;
  }
}

export function LoginForm() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const success = await authenticateCredentials(username, password);

    setIsSubmitting(false);

    if (!success) {
      setError("Invalid username or password");
      return;
    }

    router.push("/");
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-950 px-6">
      <form
        className="w-full max-w-sm space-y-6 rounded-xl border border-zinc-800 bg-zinc-900 p-8 shadow-lg"
        onSubmit={handleSubmit}
      >
        <header className="space-y-1">
          <h1 className="text-xl font-semibold text-zinc-100">Se connecter</h1>
          <p className="text-sm text-zinc-400">
            Utilisez vos identifiants Instragram pour continuer
          </p>
        </header>

        <div className="space-y-4">
          <div className="space-y-1">
            <label
              className="block text-sm font-medium text-zinc-300"
              htmlFor="username"
            >
              Nom d&apos;utilisateur ou e-mail
            </label>
            <input
              id="username"
              name="username"
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="Votre identifiant"
              autoComplete="username"
              required
            />
          </div>

          <div className="space-y-1">
            <label
              className="block text-sm font-medium text-zinc-300"
              htmlFor="password"
            >
              Mot de passe
            </label>
            <input
              id="password"
              name="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="Votre mot de passe"
              autoComplete="current-password"
              required
            />
          </div>
        </div>

        {error ? <p className="text-sm text-red-400">{error}</p> : null}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-full bg-blue-600 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting ? "Connexion..." : "Se connecter"}
        </button>

        <p className="text-center text-sm text-zinc-400">
          Mot de passe oublié ?
        </p>
      </form>
    </main>
  );
}
