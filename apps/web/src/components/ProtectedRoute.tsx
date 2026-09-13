import { Navigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";

interface Props {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

export default function ProtectedRoute({ children, requireAdmin = false }: Props) {
  const { token, user, _hasHydrated } = useAuthStore();

  // Wait for Zustand persist to finish rehydrating from localStorage before
  // deciding whether to redirect — prevents a false "not logged in" flash.
  if (!_hasHydrated) return null;

  if (!token) return <Navigate to="/login" replace />;
  if (requireAdmin && user?.role !== "admin") return <Navigate to="/" replace />;
  return <>{children}</>;
}
