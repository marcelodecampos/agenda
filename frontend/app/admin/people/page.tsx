"use client";

import { AlertTriangle, Check, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Pencil, Plus, Search, Trash2, X } from "@/components/ui/icons";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AppIconButton } from "@/components/ui/app-button";
import { AdminSidebar } from "@/components/admin/admin-sidebar";
import { CnpjField, CpfField, formatCpf } from "@/components/forms/masked-document-field";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuth } from "../../auth-provider";

type PersonType = "person" | "company";
type UserRecord = { id: string; name: string; nickname: string | null; birth_date: string | null; cpf?: string | null; cnpj?: string | null };
type Responsible = UserRecord & { cpf: string; start_date: string };

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8081";
const pageSize = 20;


export default function PeopleAdminPage() {
  const { authenticated, loading: authLoading, roles, login, apiFetch } = useAuth();
  const [type, setType] = useState<PersonType>("person");
  const [records, setRecords] = useState<UserRecord[]>([]);
  const [search, setSearch] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<UserRecord | null>(null);
  const [name, setName] = useState("");
  const [nickname, setNickname] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [document, setDocument] = useState("");
  const [editorTab, setEditorTab] = useState<"basic" | "responsibles">("basic");
  const [responsibleAddOpen, setResponsibleAddOpen] = useState(false);
  const [responsibles, setResponsibles] = useState<Responsible[]>([]);
  const [selectedResponsibles, setSelectedResponsibles] = useState<Set<string>>(new Set());
  const [responsibleCpf, setResponsibleCpf] = useState("");
  const [responsibleName, setResponsibleName] = useState("");
  const [responsibleLookup, setResponsibleLookup] = useState<UserRecord | null>(null);
  const [responsibleNotFound, setResponsibleNotFound] = useState(false);
  const [responsibleLoading, setResponsibleLoading] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<UserRecord | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const requestSequence = useRef(0);
  const isAdmin = roles.includes("platform_admin");
  const isPerson = type === "person";
  const resource = isPerson ? "persons" : "companies";
  const documentLabel = isPerson ? "CPF" : "CNPJ";

  const loadRecords = useCallback(async () => {
    const requestId = ++requestSequence.current;
    setLoading(true);
    setError("");
    try {
      const query = search.trim() ? `?search=${encodeURIComponent(search.trim())}` : "";
      const response = await apiFetch(`${apiUrl}/admin/${resource}${query}`);
      if (!response.ok) throw new Error("Não foi possível carregar os registros.");
      const nextRecords = (await response.json()) as UserRecord[];
      if (requestId !== requestSequence.current) return;
      setRecords(nextRecords);
    } catch {
      if (requestId === requestSequence.current) {
        setError("Não foi possível carregar os registros.");
      }
    } finally {
      if (requestId === requestSequence.current) setLoading(false);
    }
  }, [apiFetch, resource, search]);

  useEffect(() => {
    if (!authenticated || !isAdmin) return;
    queueMicrotask(() => void loadRecords());
  }, [authenticated, isAdmin, loadRecords]);

  const loadResponsibles = useCallback(async () => {
    if (!editing || isPerson) return;
    setResponsibleLoading(true);
    try {
      const response = await apiFetch(`${apiUrl}/admin/companies/${editing.id}/responsibles`);
      if (!response.ok) throw new Error("Não foi possível carregar os responsáveis.");
      setResponsibles((await response.json()) as Responsible[]);
      setSelectedResponsibles(new Set());
    } catch {
      setError("Não foi possível carregar os responsáveis.");
    } finally {
      setResponsibleLoading(false);
    }
  }, [apiFetch, editing, isPerson]);

  useEffect(() => {
    if (!editorOpen || editorTab !== "responsibles" || !editing || isPerson) return;
    queueMicrotask(() => void loadResponsibles());
  }, [editorOpen, editorTab, editing, isPerson, loadResponsibles]);

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const totalPages = Math.max(1, Math.ceil(records.length / pageSize));
  const visibleRecords = useMemo(() => records.slice((page - 1) * pageSize, page * pageSize), [page, records]);

  function startCreate() {
    setEditorOpen(true); setEditing(null); setEditorTab("basic"); setName(""); setNickname(""); setBirthDate(""); setDocument("");
  }

  function startEdit(record: UserRecord) {
    setSelected(new Set());
    setEditorOpen(true); setEditing(record); setEditorTab("basic"); setResponsibleAddOpen(false); setResponsibles([]); setName(record.name); setNickname(record.nickname ?? ""); setBirthDate(record.birth_date ?? ""); setDocument(isPerson ? formatCpf(record.cpf) : record.cnpj ?? "");
  }

  function cancelEdit() {
    setEditorOpen(false); setEditing(null); setEditorTab("basic"); setResponsibleAddOpen(false); setName(""); setNickname(""); setBirthDate(""); setDocument(""); setResponsibleCpf(""); setResponsibleName(""); setResponsibleLookup(null); setResponsibleNotFound(false);
  }

  function startResponsibleAdd() {
    setResponsibleAddOpen(true); setResponsibleCpf(""); setResponsibleName(""); setResponsibleLookup(null); setResponsibleNotFound(false); setError("");
  }

  function cancelResponsibleAdd() {
    setResponsibleAddOpen(false); setResponsibleCpf(""); setResponsibleName(""); setResponsibleLookup(null); setResponsibleNotFound(false); setError("");
  }

  async function lookupResponsible(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    if (!editing || isPerson || !responsibleCpf.trim()) return;
    setResponsibleLoading(true); setError(""); setResponsibleLookup(null); setResponsibleNotFound(false);
    try {
      const response = await apiFetch(`${apiUrl}/admin/companies/${editing.id}/responsibles/lookup?cpf=${encodeURIComponent(responsibleCpf.trim())}`);
      if (response.status === 404) { setResponsibleNotFound(true); return; }
      if (!response.ok) throw new Error("Não foi possível consultar o CPF.");
      setResponsibleLookup((await response.json()) as UserRecord);
    } catch (lookupError) { setError(lookupError instanceof Error ? lookupError.message : "Não foi possível consultar o CPF."); } finally { setResponsibleLoading(false); }
  }

  async function addResponsible(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    if (!editing || isPerson) return;
    setSaving(true); setError("");
    try {
      const response = await apiFetch(`${apiUrl}/admin/companies/${editing.id}/responsibles`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ cpf: responsibleCpf, name: (responsibleLookup?.name ?? responsibleName) || null }) });
      if (!response.ok) { const body = (await response.json().catch(() => null)) as { detail?: string } | null; throw new Error(body?.detail ?? "Não foi possível incluir o responsável."); }
      setResponsibleCpf(""); setResponsibleName(""); setResponsibleLookup(null); setResponsibleNotFound(false); await loadResponsibles(); showToast("Responsável incluído.");
    } catch (addError) { setError(addError instanceof Error ? addError.message : "Não foi possível incluir o responsável."); } finally { setSaving(false); }
  }

  async function removeResponsible(personId: string) {
    if (!editing) return;
    setSaving(true);
    try {
      const response = await apiFetch(`${apiUrl}/admin/companies/${editing.id}/responsibles/${personId}`, { method: "DELETE" });
      if (!response.ok) throw new Error("Não foi possível remover o responsável.");
      await loadResponsibles(); showToast("Responsável removido.");
    } catch (removeError) { setError(removeError instanceof Error ? removeError.message : "Não foi possível remover o responsável."); } finally { setSaving(false); }
  }

  async function saveRecord(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true); setError("");
    try {
      const response = await apiFetch(editing ? `${apiUrl}/admin/${resource}/${editing.id}` : `${apiUrl}/admin/${resource}`, {
        method: editing ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, nickname: nickname || null, birth_date: birthDate || null, [isPerson ? "cpf" : "cnpj"]: document || null }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(body?.detail ?? "Não foi possível salvar o registro.");
      }
      cancelEdit(); await loadRecords(); showToast(editing ? "Registro atualizado." : "Registro criado.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Não foi possível salvar o registro.");
    } finally { setSaving(false); }
  }

  async function deleteRecord() {
    if (!deleteTarget) return;
    setSaving(true);
    try {
      const response = await apiFetch(`${apiUrl}/admin/${resource}/${deleteTarget.id}`, { method: "DELETE" });
      if (!response.ok) throw new Error("Não foi possível excluir o registro.");
      setDeleteTarget(null); await loadRecords(); showToast("Registro excluído.");
    } catch (deleteError) { setError(deleteError instanceof Error ? deleteError.message : "Não foi possível excluir o registro."); } finally { setSaving(false); }
  }

  function showToast(message: string) { setToast(message); window.setTimeout(() => setToast(""), 3000); }
  function toggleSelection(id: string) { setSelected((current) => { const next = new Set(current); if (next.has(id)) next.delete(id); else next.add(id); return next; }); }
  function toggleAll() { setSelected((current) => current.size === visibleRecords.length ? new Set() : new Set(visibleRecords.map((record) => record.id))); }
  function toggleResponsible(id: string) { setSelectedResponsibles((current) => { const next = new Set(current); if (next.has(id)) next.delete(id); else next.add(id); return next; }); }
  function toggleAllResponsibles() { setSelectedResponsibles((current) => current.size === responsibles.length ? new Set() : new Set(responsibles.map((responsible) => responsible.id))); }
  function changeType(nextType: PersonType) {
    if (nextType === type) return;
    requestSequence.current += 1;
    cancelEdit();
    setType(nextType);
    setRecords([]);
    setPage(1);
    setSelected(new Set());
    setSearch("");
    setSearchOpen(false);
    setError("");
  }

  const pagination = (
    <nav className="catalog-pagination" aria-label={`Paginação de ${isPerson ? "pessoas físicas" : "pessoas jurídicas"}`}>
      <span className="catalog-range">Página {page} de {totalPages}</span>
      <div className="page-buttons"><button id="people-first-page" type="button" onClick={() => setPage(1)} disabled={page === 1} title="Primeira página" aria-label="Primeira página"><ChevronsLeft size={15} /></button><button id="people-previous-page" type="button" onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page === 1} title="Página anterior" aria-label="Página anterior"><ChevronLeft size={15} /></button><button id="people-current-page" className="page-button active" type="button" aria-current="page">{page}</button><button id="people-next-page" type="button" onClick={() => setPage((value) => Math.min(totalPages, value + 1))} disabled={page === totalPages} title="Próxima página" aria-label="Próxima página"><ChevronRight size={15} /></button><button id="people-last-page" type="button" onClick={() => setPage(totalPages)} disabled={page === totalPages} title="Última página" aria-label="Última página"><ChevronsRight size={15} /></button></div>
    </nav>
  );

  if (authLoading) return <main id="people-admin-loading" className="admin-loading">Verificando acesso...</main>;
  if (!authenticated) return <main id="people-admin-login" className="admin-gate"><p className="eyebrow">Administração</p><h1>Entre para continuar.</h1><p>Esta área é restrita aos administradores da plataforma.</p><button id="people-login-button" type="button" onClick={() => void login()}>Entrar</button></main>;
  if (!isAdmin) return <main id="people-admin-forbidden" className="admin-gate"><p className="eyebrow">Acesso restrito</p><h1>Você não tem acesso a esta área.</h1><p>Este cadastro é administrado pela plataforma.</p></main>;

  return (
    <main id="people-admin" className="admin-area">
      <AdminSidebar id="people-admin-sidebar" groups={[{ id: "people-group-tables", label: "Tabelas", items: [{ id: "people-nav-genders", label: "Gênero", href: "/admin/genders" }] }, { id: "people-group-people", label: "Pessoa", items: [{ id: "people-nav-persons", label: "Pessoa física", href: "/admin/people", active: isPerson, onClick: () => changeType("person") }, { id: "people-nav-companies", label: "Pessoa jurídica", href: "/admin/people", active: !isPerson, onClick: () => changeType("company") }] }, { id: "people-group-layout", label: "Elementos de layout", items: [{ id: "people-nav-buttons", label: "Botões", href: "/admin/button-lab" }] }]} />
      <section id="people-admin-content" className={`admin-content${editorOpen ? " gender-editor-content" : ""}`}>
        {editorOpen ? (
          <div id="people-editor-form" className="gender-editor-screen people-editor-screen">
            {!isPerson && editing && <div id="company-editor-tabs" className="organization-tabs"><button id="company-basic-tab" className={editorTab === "basic" ? "organization-tab active" : "organization-tab"} type="button" onClick={() => setEditorTab("basic")}>Dados básicos</button><button id="company-responsibles-tab" className={editorTab === "responsibles" ? "organization-tab active" : "organization-tab"} type="button" onClick={() => setEditorTab("responsibles")}>Responsáveis</button></div>}
            {editorTab === "basic" || isPerson ? <form id="people-basic-form" onSubmit={saveRecord}>
              <label htmlFor="people-name"><span>Nome</span><input id="people-name" maxLength={255} required value={name} onChange={(event) => setName(event.target.value)} /></label>
              <label htmlFor="people-nickname"><span>Nome social</span><input id="people-nickname" maxLength={255} value={nickname} onChange={(event) => setNickname(event.target.value)} /></label>
              <label htmlFor="people-birth-date"><span>Data de nascimento</span><input id="people-birth-date" type="date" value={birthDate} onChange={(event) => setBirthDate(event.target.value)} /></label>
              {isPerson ? <CpfField id="people-document" value={document} onChange={setDocument} /> : <CnpjField id="people-document" value={document} onChange={setDocument} />}
              <div className="editor-actions"><AppIconButton id="people-save-button" type="submit" variant="success" size="icon" disabled={saving} title="Salvar" aria-label="Salvar"><Check size={17} /></AppIconButton><AppIconButton id="people-cancel-button" type="button" variant="danger" onClick={cancelEdit} size="icon" title="Cancelar" aria-label="Cancelar"><X size={17} /></AppIconButton></div>
            </form> : <section id="company-responsibles-panel" className="company-responsibles-panel">
              {responsibleAddOpen ? <>
                <form id="responsible-lookup-form" className="responsible-lookup-form" onSubmit={lookupResponsible}><CpfField id="responsible-cpf" value={responsibleCpf} onChange={setResponsibleCpf} required /><AppIconButton id="responsible-lookup-button" className="icon-action search-icon" type="submit" variant="outline" size="icon" disabled={responsibleLoading} title="Consultar CPF" aria-label="Consultar CPF"><Search size={17} color="#1e5d7d" /></AppIconButton></form>
                {responsibleLookup && <div id="responsible-found" className="responsible-found"><strong>{responsibleLookup.name}</strong><span>{responsibleLookup.cpf}</span><AppIconButton id="responsible-add-found" className="icon-action add-icon" type="button" variant="success" size="icon" onClick={() => void addResponsible()} title="Incluir responsável" aria-label="Incluir responsável"><Plus size={17} color="#28734b" /></AppIconButton></div>}
                {responsibleNotFound && <form id="responsible-create-form" className="responsible-create-form" onSubmit={addResponsible}><p className="message">Pessoa não encontrada. Informe o nome para criar o responsável.</p><label htmlFor="responsible-name"><span>Nome</span><input id="responsible-name" required value={responsibleName} onChange={(event) => setResponsibleName(event.target.value)} /></label><AppIconButton id="responsible-create-button" className="icon-action add-icon" type="submit" variant="success" size="icon" disabled={saving} title="Criar e incluir" aria-label="Criar e incluir"><Check size={17} color="#28734b" /></AppIconButton></form>}
                {responsibleLoading && <p id="responsibles-loading" className="message">Consultando...</p>}
                <AppIconButton id="responsible-back-button" className="icon-action danger-icon responsible-back-button" type="button" variant="danger" size="icon" onClick={cancelResponsibleAdd} title="Voltar para responsáveis" aria-label="Voltar para responsáveis"><X size={17} color="#b84f42" /></AppIconButton>
              </> : <>
                <div id="responsibles-list-actions" className="responsibles-list-actions"><AppIconButton id="responsible-add-button" className="icon-action add-icon" type="button" variant="outline" size="icon" onClick={startResponsibleAdd} title="Incluir responsável" aria-label="Incluir responsável"><Plus size={17} color="#1e5d7d" /></AppIconButton></div>
                <div id="responsibles-list" className="responsibles-list"><h3>Responsáveis ativos</h3><Table id="responsibles-table" className="gender-data-table"><TableHeader id="responsibles-table-header"><TableRow id="responsibles-header-row"><TableHead id="responsibles-name-header"><label><input id="responsibles-select-all" type="checkbox" checked={responsibles.length > 0 && selectedResponsibles.size === responsibles.length} onChange={toggleAllResponsibles} aria-label="Selecionar todos os responsáveis" />Nome</label></TableHead><TableHead id="responsibles-actions-header" className="gender-action-column">Ações</TableHead></TableRow></TableHeader><TableBody id="responsibles-table-body">{responsibles.map((responsible) => <TableRow id={`responsible-row-${responsible.id}`} className={selectedResponsibles.has(responsible.id) ? "selected" : undefined} key={responsible.id}><TableCell id={`responsible-name-${responsible.id}`}><label><input id={`responsible-select-${responsible.id}`} type="checkbox" checked={selectedResponsibles.has(responsible.id)} onChange={() => toggleResponsible(responsible.id)} aria-label={`Selecionar ${responsible.name}`} /><strong>{responsible.name}</strong></label></TableCell><TableCell id={`responsible-actions-${responsible.id}`} className="gender-action-column"><button id={`responsible-remove-${responsible.id}`} className="icon-action danger-icon" type="button" onClick={() => void removeResponsible(responsible.id)} title="Remover responsável" aria-label={`Remover ${responsible.name}`}><Trash2 size={15} color="#b84f42" /></button></TableCell></TableRow>)}</TableBody></Table></div>
              </>}
            </section>}
            {error && <p className="message error" role="alert">{error}</p>}
          </div>
        ) : (
          <>
            <header id="people-admin-heading" className="admin-heading"><div><p className="eyebrow">Cadastro do sistema</p><div className="admin-title-line"><h1 className="admin-page-title">{isPerson ? "Pessoas físicas" : "Pessoas jurídicas"}</h1><span className="admin-badge">Administrador</span></div></div></header>
            <section id="people-catalog-panel" className="catalog-panel" aria-label={`Gerenciamento de ${isPerson ? "pessoas físicas" : "pessoas jurídicas"}`}>
              <div id="people-catalog-actions" className="catalog-heading"><div className="catalog-heading-actions"><AppIconButton id="people-add-button" className="icon-action add-icon" type="button" variant="outline" size="icon" onClick={startCreate} title="Adicionar" aria-label="Adicionar"><Plus size={17} /></AppIconButton><button id="people-search-button" className="icon-action search-icon" type="button" onClick={() => setSearchOpen((value) => !value)} title="Pesquisar" aria-label="Pesquisar"><Search size={17} /></button></div></div>
              {searchOpen && <div id="people-search-toolbar" className="catalog-toolbar"><label htmlFor="people-search">Pesquisar</label><input id="people-search" value={search} onChange={(event) => { setPage(1); setSearch(event.target.value); }} placeholder="Nome" /><span className="catalog-range">{records.length} registro{records.length === 1 ? "" : "s"}</span></div>}
              {error && <p id="people-error" className="message error" role="alert">{error}</p>}
              {loading && <p id="people-loading" className="message">Carregando registros...</p>}
              {!loading && visibleRecords.length === 0 && <p id="people-empty" className="message">Nenhum registro encontrado.</p>}
              {!loading && visibleRecords.length > 0 && <><div id="people-pagination-top">{pagination}</div><Table id="people-table" className="gender-data-table"><TableHeader id="people-table-header"><TableRow id="people-header-row"><TableHead id="people-select-header"><label><input id="people-select-all" type="checkbox" checked={selected.size === visibleRecords.length} onChange={toggleAll} aria-label="Selecionar todos" />Nome</label></TableHead><TableHead id="people-document-header">{documentLabel}</TableHead><TableHead id="people-actions-header" className="gender-action-column">Ações</TableHead></TableRow></TableHeader><TableBody id="people-table-body">{visibleRecords.map((record) => <TableRow id={`people-row-${record.id}`} className={selected.has(record.id) ? "selected" : undefined} key={record.id}><TableCell id={`people-name-${record.id}`}><label><input id={`people-select-${record.id}`} type="checkbox" checked={selected.has(record.id)} onChange={() => toggleSelection(record.id)} aria-label={`Selecionar ${record.name}`} /><span>{record.name}</span></label></TableCell><TableCell id={`people-document-${record.id}`}>{isPerson ? record.cpf || "" : record.cnpj || ""}</TableCell><TableCell id={`people-actions-${record.id}`} className="gender-action-column"><div className="row-actions"><button id={`people-edit-${record.id}`} className="icon-action subtle" type="button" onClick={() => startEdit(record)} disabled={selected.size > 0} title="Editar" aria-label={`Editar ${record.name}`}><Pencil size={15} /></button><button id={`people-delete-${record.id}`} className="icon-action danger-icon" type="button" onClick={() => setDeleteTarget(record)} title="Excluir" aria-label={`Excluir ${record.name}`}><Trash2 size={15} /></button></div></TableCell></TableRow>)}</TableBody></Table><div id="people-pagination-bottom">{pagination}</div></>}
            </section>
          </>
        )}
      </section>
      {toast && <p id="people-toast" className="toast-message" role="status">{toast}</p>}
      {deleteTarget && <div id="people-delete-dialog" className="confirm-backdrop" role="presentation"><div className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="people-delete-title"><span className="attention-icon"><AlertTriangle size={20} /></span><div className="confirm-content"><h3 id="people-delete-title">Excluir cadastro?</h3><p>O registro <strong>{deleteTarget.name}</strong> será removido.</p><div className="confirm-actions"><button id="people-delete-cancel" className="cancel-action" type="button" onClick={() => setDeleteTarget(null)}>Cancelar</button><button id="people-delete-confirm" className="danger-button" type="button" onClick={() => void deleteRecord()} disabled={saving}>Excluir</button></div></div></div></div>}
    </main>
  );
}
