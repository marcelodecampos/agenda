"use client";

import { AlertTriangle, Check, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Pencil, Plus, Search, Trash2, X } from "@/components/ui/icons";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "../../auth-provider";
import { AppIconButton } from "@/components/ui/app-button";
import { AdminSidebar } from "@/components/admin/admin-sidebar";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Gender = {
  id: string;
  description: string;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8081";
const pageSize = 20;

export default function GenderAdminPage() {
  const { authenticated, loading: authLoading, roles, login, apiFetch } = useAuth();
  const [genders, setGenders] = useState<Gender[]>([]);
  const [search, setSearch] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<Gender | null>(null);
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [page, setPage] = useState(1);
  const [deleteTarget, setDeleteTarget] = useState<Gender | null>(null);

  const isAdmin = roles.includes("platform_admin");

  const loadGenders = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = search.trim() ? `?search=${encodeURIComponent(search.trim())}` : "";
      const response = await apiFetch(`${apiUrl}/admin/genders${params}`);
      if (!response.ok) throw new Error("Não foi possível carregar o catálogo.");
      setGenders((await response.json()) as Gender[]);
      setSelected(new Set());
    } catch {
      setError("Não foi possível carregar o catálogo de gêneros.");
    } finally {
      setLoading(false);
    }
  }, [apiFetch, search]);

  useEffect(() => {
    if (!authenticated || !isAdmin) return;
    queueMicrotask(() => void loadGenders());
  }, [authenticated, isAdmin, loadGenders]);

  const totalPages = Math.max(1, Math.ceil(genders.length / pageSize));
  const visibleGenders = useMemo(
    () => genders.slice((page - 1) * pageSize, page * pageSize),
    [genders, page],
  );

  function startCreate() {
    setEditorOpen(true);
    setEditing(null);
    setDescription("");
  }

  function startEdit(gender: Gender) {
    setEditorOpen(true);
    setEditing(gender);
    setDescription(gender.description);
  }

  function cancelEdit() {
    setEditorOpen(false);
    setEditing(null);
    setDescription("");
  }

  async function saveGender(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = description.trim();
    if (!value) return;
    setSaving(true);
    setError("");
    try {
      const response = await apiFetch(
        editing ? `${apiUrl}/admin/genders/${editing.id}` : `${apiUrl}/admin/genders`,
        {
          method: editing ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ description: value }),
        },
      );
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(payload?.detail ?? "Não foi possível salvar o gênero.");
      }
      cancelEdit();
      await loadGenders();
      showToast(editing ? "Gênero atualizado." : "Gênero criado.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Não foi possível salvar o gênero.");
    } finally {
      setSaving(false);
    }
  }

  async function deleteGender() {
    if (!deleteTarget) return;
    setSaving(true);
    try {
      const response = await apiFetch(`${apiUrl}/admin/genders/${deleteTarget.id}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(payload?.detail ?? "Não foi possível excluir o gênero.");
      }
      setDeleteTarget(null);
      await loadGenders();
      showToast("Gênero excluído.");
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Não foi possível excluir o gênero.");
    } finally {
      setSaving(false);
    }
  }

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(""), 3000);
  }

  function toggleSelection(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected((current) =>
      current.size === visibleGenders.length
        ? new Set()
        : new Set(visibleGenders.map((gender) => gender.id)),
    );
  }

  const paginationControls = (
    <nav className="catalog-pagination" aria-label="Paginação da tabela de gêneros">
      <span className="catalog-range">Página {page} de {totalPages}</span>
      <div className="page-buttons">
        <button type="button" onClick={() => setPage(1)} disabled={page === 1} title="Primeira página" aria-label="Primeira página"><ChevronsLeft size={15} /></button>
        <button type="button" onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page === 1} title="Página anterior" aria-label="Página anterior"><ChevronLeft size={15} /></button>
        <button className="page-button active" type="button" aria-current="page">{page}</button>
        <button type="button" onClick={() => setPage((value) => Math.min(totalPages, value + 1))} disabled={page === totalPages} title="Próxima página" aria-label="Próxima página"><ChevronRight size={15} /></button>
        <button type="button" onClick={() => setPage(totalPages)} disabled={page === totalPages} title="Última página" aria-label="Última página"><ChevronsRight size={15} /></button>
      </div>
    </nav>
  );

  if (authLoading) return <main className="admin-loading">Verificando acesso...</main>;

  if (!authenticated) {
    return (
      <main className="admin-gate">
        <p className="eyebrow">Administração</p>
        <h1>Entre para continuar.</h1>
        <p>Esta área é restrita aos administradores da plataforma.</p>
        <button type="button" onClick={() => void login()}>Entrar</button>
      </main>
    );
  }

  if (!isAdmin) {
    return (
      <main className="admin-gate">
        <p className="eyebrow">Acesso restrito</p>
        <h1>Você não tem acesso a esta área.</h1>
        <p>O catálogo de gêneros é administrado pela plataforma.</p>
      </main>
    );
  }

  return (
    <main className="admin-area">
      <AdminSidebar id="gender-admin-sidebar" groups={[{ id: "gender-group-tables", label: "Tabelas", items: [{ id: "gender-nav-genders", label: "Gênero", href: "/admin/genders", active: true }] }, { id: "gender-group-people", label: "Pessoa", items: [{ id: "gender-nav-persons", label: "Pessoa física", href: "/admin/people" }, { id: "gender-nav-companies", label: "Pessoa jurídica", href: "/admin/people" }] }, { id: "gender-group-layout", label: "Elementos de layout", items: [{ id: "gender-nav-buttons", label: "Botões", href: "/admin/button-lab" }] }]} />

      <section className={`admin-content${editorOpen ? " gender-editor-content" : ""}`}>
        {editorOpen ? (
          <form className="gender-editor-screen" onSubmit={saveGender}>
            <label htmlFor="gender-description"><span>Descrição</span><input id="gender-description" maxLength={255} required value={description} onChange={(event) => setDescription(event.target.value)} /></label>
            <div className="editor-actions"><AppIconButton id="gender-save-button" type="submit" variant="success" size="icon" disabled={saving} title="Salvar" aria-label="Salvar"><Check size={17} /></AppIconButton><AppIconButton id="gender-cancel-button" type="button" variant="danger" size="icon" onClick={cancelEdit} title="Cancelar" aria-label="Cancelar"><X size={17} /></AppIconButton></div>
            {error && <p className="message error" role="alert">{error}</p>}
          </form>
        ) : (
        <>
          <header className="admin-heading">
            <div>
              <p className="eyebrow">Catálogo do sistema</p>
              <div className="admin-title-line">
                <h1 className="admin-page-title">Gêneros</h1>
                <span className="admin-badge">Administrador</span>
              </div>
            </div>
          </header>

          <section className="catalog-panel" aria-label="Gerenciamento de gêneros">
          <div className="catalog-heading">
            <div className="catalog-heading-actions">
              <AppIconButton className="icon-action add-icon" id="gender-add-button" type="button" variant="outline" size="icon" onClick={startCreate} title="Adicionar gênero" aria-label="Adicionar gênero"><Plus size={17} /></AppIconButton>
              <button className="icon-action search-icon" type="button" onClick={() => setSearchOpen((value) => !value)} title="Pesquisar gêneros" aria-label="Pesquisar gêneros"><Search size={17} /></button>
            </div>
          </div>

          {searchOpen && (
            <div className="catalog-toolbar">
              <label htmlFor="gender-search">Pesquisar</label>
              <input id="gender-search" value={search} onChange={(event) => { setPage(1); setSearch(event.target.value); }} placeholder="Descrição" />
              <span className="catalog-range">{genders.length} registro{genders.length === 1 ? "" : "s"}</span>
            </div>
          )}

          {error && <p className="message error" role="alert">{error}</p>}
          {loading && <p className="message">Carregando registros...</p>}
          {!loading && visibleGenders.length === 0 && <p className="message">Nenhum gênero encontrado.</p>}

          {!loading && visibleGenders.length > 0 && (
            <>
              {paginationControls}
              <Table id="gender-table" className="gender-data-table">
                <TableHeader id="gender-table-header">
                  <TableRow id="gender-header-row" className="gender-table-header">
                    <TableHead id="gender-description-header"><label><input id="gender-select-all" type="checkbox" checked={visibleGenders.length > 0 && selected.size === visibleGenders.length} onChange={toggleAll} aria-label="Selecionar todos" />Descrição</label></TableHead>
                    <TableHead id="gender-actions-header" className="gender-action-column">Ações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody id="gender-table-body">
                {visibleGenders.map((gender) => (
                  <TableRow id={`gender-row-${gender.id}`} className={selected.has(gender.id) ? "selected" : undefined} key={gender.id}>
                    <TableCell id={`gender-description-${gender.id}`}><label><input id={`gender-select-${gender.id}`} type="checkbox" checked={selected.has(gender.id)} onChange={() => toggleSelection(gender.id)} aria-label={`Selecionar ${gender.description}`} /><span>{gender.description}</span></label></TableCell>
                    <TableCell id={`gender-actions-${gender.id}`} className="gender-action-column"><div className="row-actions"><button id={`gender-edit-${gender.id}`} className="icon-action subtle" type="button" onClick={() => startEdit(gender)} disabled={selected.size > 0} title="Editar" aria-label={`Editar ${gender.description}`}><Pencil size={15} /></button><button id={`gender-delete-${gender.id}`} className="icon-action danger-icon" type="button" onClick={() => setDeleteTarget(gender)} title="Excluir" aria-label={`Excluir ${gender.description}`}><Trash2 size={15} /></button></div></TableCell>
                  </TableRow>
                ))}
                </TableBody>
              </Table>
              {paginationControls}
            </>
          )}
          </section>
        </>
        )}
      </section>

      {toast && <p className="toast-message" role="status">{toast}</p>}
      {deleteTarget && (
        <div className="confirm-backdrop" role="presentation">
          <div className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="delete-title">
            <span className="attention-icon"><AlertTriangle size={20} /></span>
            <div className="confirm-content"><h3 id="delete-title">Excluir gênero?</h3><p>O registro <strong>{deleteTarget.description}</strong> será removido do catálogo.</p><div className="confirm-actions"><button className="cancel-action" type="button" onClick={() => setDeleteTarget(null)}>Cancelar</button><button className="danger-button" type="button" onClick={() => void deleteGender()} disabled={saving}>Excluir</button></div></div>
          </div>
        </div>
      )}
    </main>
  );
}
