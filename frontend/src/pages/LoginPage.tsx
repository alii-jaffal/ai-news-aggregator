import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { api } from "../api";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const sessionQuery = useQuery({
    queryKey: ["session"],
    queryFn: () => api.getSession(),
  });

  const loginMutation = useMutation({
    mutationFn: () => api.login({ username, password }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["session"] });
      const target =
        typeof location.state === "object" &&
        location.state !== null &&
        "from" in location.state &&
        typeof location.state.from === "string"
          ? location.state.from
          : "/admin";
      navigate(target, { replace: true });
    },
  });

  if (sessionQuery.isLoading) {
    return <div className="empty-state">Checking dashboard session...</div>;
  }

  if (sessionQuery.data?.authenticated) {
    return <Navigate to="/admin" replace />;
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void loginMutation.mutateAsync();
  };

  return (
    <div className="login-shell">
      <section className="login-card">
        <div className="login-card__header">
          <p className="panel__eyebrow">Admin access</p>
          <h1>Dashboard sign in</h1>
          <p>
            Use the dashboard admin credentials from your root <code>.env</code>. The public
            homepage lives separately from this internal admin console.
          </p>
        </div>
        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            <span>Username</span>
            <input value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <label>
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          <button className="primary-button" type="submit" disabled={loginMutation.isPending}>
            {loginMutation.isPending ? "Signing in..." : "Sign in"}
          </button>
        </form>
        {loginMutation.error ? (
          <div className="inline-alert inline-alert-danger">
            {(loginMutation.error as Error).message}
          </div>
        ) : null}
      </section>
    </div>
  );
}
