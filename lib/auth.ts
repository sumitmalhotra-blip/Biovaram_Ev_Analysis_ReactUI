import NextAuth from "next-auth"
import Credentials from "next-auth/providers/credentials"

// User type for the session
export interface User {
  id: string
  email: string
  name: string
  role: "user" | "admin" | "researcher" | "lab_manager"
  organization?: string | null
  createdAt?: string
}

// Extend the built-in session types
declare module "next-auth" {
  interface Session {
    user: User
  }
}

// API base URL for backend  
let API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
// Safety: Remove trailing /api/v1 if present (prevents double prefix bug)
if (API_BASE.endsWith("/api/v1")) {
  API_BASE = API_BASE.replace(/\/api\/v1$/, "")
}
const API_URL = `${API_BASE}/api/v1`

export const { handlers, signIn, signOut, auth } = NextAuth({
  pages: {
    signIn: "/login",
    error: "/login",
  },
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  providers: [
    Credentials({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          throw new Error("Email and password are required")
        }

        try {
          // Call backend API to authenticate user
          const response = await fetch(`${API_URL}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
            }),
          })

          if (!response.ok) {
            const error = await response.json()
            throw new Error(error.detail || "Invalid credentials")
          }

          const data = await response.json()
          
          if (data.user) {
            return {
              id: data.user.id.toString(),
              email: data.user.email,
              name: data.user.name,
              role: data.user.role || "user",
              organization: data.user.organization,
            }
          }

          return null
        } catch (error) {
          console.error("Auth error:", error)
          throw error
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id
        token.email = user.email
        token.name = user.name
        token.role = (user as User).role
        token.organization = (user as User).organization
      }
      return token
    },
    async session({ session, token }) {
      if (token && session.user) {
        session.user.id = token.id as string
        session.user.email = token.email as string
        session.user.name = token.name as string
        session.user.role = token.role as "user" | "admin" | "researcher" | "lab_manager"
        session.user.organization = token.organization as string | null
      }
      return session
    },
  },
  trustHost: true,
})
