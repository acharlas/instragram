"use client";

import { useRouter } from "next/navigation";
import { signIn } from "next-auth/react";
import { useState } from "react";

import type { RegisterResult } from "../page";

type RegisterFormProps = {
  action: (formData: FormData) => Promise<RegisterResult>;
};

const isNonEmpty = (value: string) => value.trim().length > 0;

export function RegisterForm({ action }: RegisterFormProps) {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!isNonEmpty(username) || !isNonEmpty(email) || !isNonEmpty(password)) {
      setError("Tous les champs sont requis");
      return;
    }

    setError(null);
    setIsSubmitting(true);

    const formData = new FormData(event.currentTarget);
    const result = await action(formData);

    if (!result.success) {
      setIsSubmitting(false);
      setError(result.error ?? "Inscription impossible");
      return;
    }

    const loginResult = await signIn("credentials", {
      username,
      password,
      redirect: false,
    });

    if (loginResult?.error) {
      setIsSubmitting(false);
      setError("Compte créé, mais connexion échouée");
      router.push("/login");
      return;
    }

    router.push("/");
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-950 px-6">
      <form
        className="w-full max-w-md space-y-6 rounded-xl border border-zinc-800 bg-zinc-900 p-8 shadow-lg"
        onSubmit={handleSubmit}
      >
        <header className="space-y-1">
          <h1 className="text-xl font-semibold text-zinc-100">
            Créer un compte
          </h1>
          <p className="text-sm text-zinc-400">
            Rejoignez Instragram et commencez à partager dès maintenant.
          </p>
        </header>

        <div className="space-y-4">
          <div className="space-y-1">
            <label
              className="block text-sm font-medium text-zinc-300"
              htmlFor="username"
            >
              Nom d&apos;utilisateur
            </label>
            <input
              id="username"
              name="username"
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="Votre pseudo"
              required
            />
          </div>

          <div className="space-y-1">
            <label
              className="block text-sm font-medium text-zinc-300"
              htmlFor="email"
            >
              Adresse e-mail
            </label>
            <input
              id="email"
              name="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="vous@example.com"
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
              placeholder="Mot de passe sécurisé"
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
          {isSubmitting ? "Inscription..." : "S'inscrire"}
        </button>

        <button
          type="button"
          onClick={() => router.push("/login")}
          className="w-full rounded-full border border-zinc-700 py-2 text-sm font-semibold text-zinc-200 transition hover:bg-zinc-800"
        >
          Vous avez déjà un compte ?
        </button>
      </form>
    </main>
  );
}
