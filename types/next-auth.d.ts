import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  interface User {
    id: string;
    email: string;
    name?: string | null;
    role?: string;
    organization?: string | null;
  }

  interface Session {
    user: User & {
      id: string;
      role?: string;
      organization?: string | null;
    };
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    id: string;
    role?: string;
    organization?: string | null;
  }
}
