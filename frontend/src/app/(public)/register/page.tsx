import { redirect } from "next/navigation";

import { getSessionServer } from "../../../lib/auth/session";

import { RegisterForm } from "./_components/register-form";

const API_BASE_URL = process.env.BACKEND_API_URL ?? "http://backend:8000";

export type RegisterResult = {
  success: boolean;
  error?: string;
};

export async function registerUser(
  formData: FormData,
): Promise<RegisterResult> {
  "use server";

  const username = String(formData.get("username") ?? "").trim();
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "").trim();

  if (username.length < 3) {
    return {
      success: false,
      error: "Le nom d'utilisateur doit contenir au moins 3 caractères",
    };
  }

  if (!email.includes("@")) {
    return { success: false, error: "Adresse e-mail invalide" };
  }

  if (password.length < 8) {
    return {
      success: false,
      error: "Le mot de passe doit contenir au moins 8 caractères",
    };
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, email, password }),
      cache: "no-store",
    });

    if (!response.ok) {
      let detail = "Inscription impossible";
      try {
        const data = await response.json();
        if (typeof data?.detail === "string") {
          detail = data.detail;
        }
      } catch (error) {
        void error;
      }
      return { success: false, error: detail };
    }
  } catch (_error) {
    return { success: false, error: "Erreur réseau lors de l'inscription" };
  }

  return { success: true };
}

export default async function RegisterPage() {
  const session = await getSessionServer();
  if (session) {
    redirect("/");
  }

  return <RegisterForm action={registerUser} />;
}
