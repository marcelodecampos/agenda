"use client";

import { Typography } from "antd";

import { AdminSidebar } from "@/components/admin/admin-sidebar";
import { useAuth } from "../auth-provider";

export default function AdminHomePage() {
  const { authenticated, loading, roles, login } = useAuth();

  if (loading) return <main id="admin-home-loading" className="admin-loading">Verificando acesso...</main>;
  if (!authenticated) return <main id="admin-home-login" className="admin-gate"><p className="eyebrow">Administração</p><h1>Entre para continuar.</h1><button id="admin-home-login-button" type="button" onClick={() => void login()}>Entrar</button></main>;
  if (!roles.includes("platform_admin")) return <main id="admin-home-forbidden" className="admin-gate"><p className="eyebrow">Acesso restrito</p><h1>Você não tem acesso a esta área.</h1></main>;

  return <main id="admin-home" className="admin-area"><AdminSidebar id="admin-home-sidebar" groups={[{ id: "admin-home-group-tables", label: "Tabelas", items: [{ id: "admin-home-nav-genders", label: "Gênero", href: "/admin/genders" }] }, { id: "admin-home-group-people", label: "Pessoa", items: [{ id: "admin-home-nav-persons", label: "Pessoa física", href: "/admin/people" }, { id: "admin-home-nav-companies", label: "Pessoa jurídica", href: "/admin/people" }] }, { id: "admin-home-group-layout", label: "Elementos de layout", items: [{ id: "admin-home-nav-buttons", label: "Botões", href: "/admin/button-lab" }] }]} /><section id="admin-home-content" className="admin-content"><div id="admin-home-message" className="admin-home-message"><Typography.Text id="admin-home-eyebrow" type="secondary">Administração</Typography.Text><Typography.Title id="admin-home-title" level={2}>Selecione uma área</Typography.Title><Typography.Text id="admin-home-description" type="secondary">Escolha um cadastro no menu lateral para começar.</Typography.Text></div></section></main>;
}
