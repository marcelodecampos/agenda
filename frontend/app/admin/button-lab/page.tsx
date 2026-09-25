"use client";

import { ArrowRight, Check, ChevronRight, ExternalLink, Pencil, Plus, Search, Trash2, X } from "@/components/ui/icons";

import { AppButton, AppIconButton } from "@/components/ui/app-button";
import { AdminSidebar } from "@/components/admin/admin-sidebar";
import { useAuth } from "../../auth-provider";

const variants = ["default", "outline", "ghost", "success", "danger"] as const;

type ButtonVariant = (typeof variants)[number];

export default function ButtonLabPage() {
  const { authenticated, loading, roles, login } = useAuth();

  if (loading) return <main id="button-lab-loading" className="admin-loading">Verificando acesso...</main>;
  if (!authenticated) return <main id="button-lab-login" className="admin-gate"><p className="eyebrow">Administração</p><h1>Entre para continuar.</h1><button id="button-lab-login-button" type="button" onClick={() => void login()}>Entrar</button></main>;
  if (!roles.includes("platform_admin")) return <main id="button-lab-forbidden" className="admin-gate"><p className="eyebrow">Acesso restrito</p><h1>Você não tem acesso a esta área.</h1></main>;

  return (
    <main id="button-lab" className="admin-area">
      <AdminSidebar id="button-lab-sidebar" groups={[{ id: "button-lab-group-tables", label: "Tabelas", items: [{ id: "button-lab-nav-genders", label: "Gênero", href: "/admin/genders" }] }, { id: "button-lab-group-people", label: "Pessoa", items: [{ id: "button-lab-nav-persons", label: "Pessoa física", href: "/admin/people" }, { id: "button-lab-nav-companies", label: "Pessoa jurídica", href: "/admin/people" }] }, { id: "button-lab-group-layout", label: "Elementos de layout", items: [{ id: "button-lab-nav-current", label: "Botões", href: "/admin/button-lab", active: true }] }]} />
      <section id="button-lab-content" className="admin-content button-lab-content">
        <header id="button-lab-heading" className="admin-heading"><div><p className="eyebrow">Design system</p><div className="admin-title-line"><h1 className="admin-page-title">Botões</h1><span className="admin-badge">Administrador</span></div></div></header>
        <section id="button-variants" className="button-lab-section"><h2>Variantes</h2><div className="button-lab-grid">{variants.map((variant: ButtonVariant) => <div id={`button-variant-${variant}`} className="button-lab-card" key={variant}><span>{variant}</span><AppButton id={`button-${variant}`} variant={variant}>Ação</AppButton></div>)}</div></section>
        <section id="button-sizes" className="button-lab-section"><h2>Tamanhos</h2><div className="button-lab-row"><AppButton id="button-size-default" variant="default" size="default">Padrão</AppButton><AppIconButton id="button-size-icon" variant="outline" size="icon" title="Ação com ícone" aria-label="Ação com ícone"><Plus size={17} color="#1e5d7d" /></AppIconButton></div></section>
        <section id="button-label-icons" className="button-lab-section"><h2>Label + ícone</h2><div className="button-lab-row"><AppButton id="button-label-icon-add" variant="outline"><Plus size={17} color="#1e5d7d" />Adicionar</AppButton><AppButton id="button-label-icon-search" variant="default"><Search size={17} color="white" />Pesquisar</AppButton><AppButton id="button-label-icon-save" variant="success"><Check size={17} color="#28734b" />Salvar</AppButton><AppButton id="button-label-icon-delete" variant="danger"><Trash2 size={17} color="#a64b43" />Excluir</AppButton></div></section>
        <section id="button-icons-right" className="button-lab-section"><h2>Ícone à direita</h2><div className="button-lab-row"><AppButton id="button-icon-right-next" variant="outline">Continuar<ArrowRight size={17} color="#1e5d7d" /></AppButton><AppButton id="button-icon-right-details" variant="default">Ver detalhes<ChevronRight size={17} color="white" /></AppButton><AppButton id="button-icon-right-external" variant="ghost">Abrir página<ExternalLink size={17} color="#286887" /></AppButton></div></section>
        <section id="button-icon-actions" className="button-lab-section"><h2>Ações com ícone</h2><div className="button-lab-row"><AppIconButton id="button-icon-add" className="icon-action add-icon" variant="outline" size="icon" title="Adicionar" aria-label="Adicionar"><Plus size={17} color="#1e5d7d" /></AppIconButton><AppIconButton id="button-icon-search" className="icon-action search-icon" variant="outline" size="icon" title="Pesquisar" aria-label="Pesquisar"><Search size={17} color="#1e5d7d" /></AppIconButton><AppIconButton id="button-icon-edit" className="icon-action subtle" variant="ghost" size="icon" title="Editar" aria-label="Editar"><Pencil size={15} color="#286887" /></AppIconButton><AppIconButton id="button-icon-save" variant="success" size="icon" title="Salvar" aria-label="Salvar"><Check size={17} color="#28734b" /></AppIconButton><AppIconButton id="button-icon-delete" className="icon-action danger-icon" variant="danger" size="icon" title="Excluir" aria-label="Excluir"><Trash2 size={15} color="#b84f42" /></AppIconButton><AppIconButton id="button-icon-cancel" variant="danger" size="icon" title="Cancelar" aria-label="Cancelar"><X size={17} color="#a64b43" /></AppIconButton></div></section>
        <section id="button-states" className="button-lab-section"><h2>Estados</h2><div className="button-lab-row"><AppButton id="button-disabled-default" variant="default" disabled>Desabilitado</AppButton><AppIconButton id="button-disabled-icon" variant="outline" size="icon" disabled title="Desabilitado" aria-label="Desabilitado"><Search size={17} color="#1e5d7d" /></AppIconButton></div></section>
      </section>
    </main>
  );
}
