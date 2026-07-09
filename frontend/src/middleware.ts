import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const publicRoutes = ["/login", "/api/health"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Rotas de API são proxy para o backend; autenticação é tratada lá.
  if (pathname.startsWith("/api/")) {
    return NextResponse.next();
  }

  const isPublic = publicRoutes.some((route) => pathname.startsWith(route));
  const isAuthenticated = request.cookies.get("vt_auth")?.value === "1";

  if (!isPublic && !isAuthenticated) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (pathname === "/login" && isAuthenticated) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
